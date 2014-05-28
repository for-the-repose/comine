#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.core.heman  import HeMan, IHeap
from comine.maps.ring   import Ring
from comine.maps.alias  import Alias
from comine.misc.humans import Humans
from .errors			import ErrorDamaged
from .guess				import Guess
from .arena				import Arena
from .chunk				import Chunk
from .exten				import EHeap
from .scale				import Scale

@HeMan.register
class TheGlibcHeap(IHeap):
    ''' The GLibc heap validator and data miner '''

    def __init__(s, log, infer):
        frame   = gdb.selected_frame()

        s.__log     = log
        s.__infer   = infer
        s.__libc    = infer.__libc__()
        s.__ready   = False
        s.__ring    = Ring()
        s.__arena   = []
        s.__mp      = frame.read_var('mp_')

        s.__sc = Scale(s.__libc, page = s.__disq_page_size())

        s.__log(4, 'heap page size=%ub' % s.__sc.__page__())
        s.__log(1, "building glibc arena list")

        arena = frame.read_var('main_arena')

        if arena.type.code != gdb.TYPE_CODE_STRUCT:
            raise Exception('invalid main arena symbol')

        arena_t = arena.type.pointer()

        arena = gdb.Value(arena.address).cast(arena_t)

        while s.__try_to_add_arena(arena): arena = arena['next']

        s.__log(1, "heap has %i arena items" % len(s.__arena))

        segment = s.__mp['sbrk_base']

        if segment.type.code != gdb.TYPE_CODE_PTR:
            raise Exception('data segment base type invalid')

        s.__ready = True

        infer.__world__().push(s, s.__ring, provide = 'heap')

        Guess(log, s.__infer.__world__(), s.__ring, sc = s.__sc)()

        s.__examine_mmaps()

    @classmethod
    def __who__(cls):   return 'glibc'

    def __ready__(s):   return s.__ready

    def __disq_page_size(s):
        _pre_2_17 = lambda : s.__mp['pagesize']

        def _post_2_17():
            frame = gdb.selected_frame()

            return frame.read_var('_rtld_global_ro')['_dl_pagesize']

        for hope in (_pre_2_17, _post_2_17):
            try:
                return long(hope())

            except Exception as E:
                pass

        raise Exception('Cannot discover page size')

    def __try_to_add_arena(s, _arena):
        at, seq = s.__libc.addr(_arena), len(s.__arena)

        if seq == 0:
            s.__log(1, 'primary arena entry at 0x%x' % at)

        if not s.__arena_by_addr(at):
            if not s.__infer.validate(at):
                raise Exception('Arena ptr refers to nowhere')

            try:
                arena = s.__make_arena(_arena, seq)

            except ErrorDamaged as E:
                s.__log(1, 'cannot add arena at 0x%x, error %s' % (at, E))

            else:
                s.__arena.append(arena)

                s.__log(1, 'arena #%i at 0x%x discovered'
                            % (arena.__seq__(), arena.__at__()))

                return True

    def __make_arena(s, _arena, seq):
        return Arena(s.__sc, _arena, seq, s.__ring, s.__log, s.__infer)

    def __examine_mmaps(s):
        ''' Analyse mmap() settings for the heap.

            DEFAULT_MMAP_THRESHOLD_{MIN,MAX} preprocessor macro
            defines lower and upper limit of mmapped regions.
        '''

        s.__mmapped     = int(s.__mp['mmapped_mem'])
        s.__mmaps       = int(s.__mp['n_mmaps'])
        s.__mmap_th     = int(s.__mp['mmap_threshold'])
        s.__mmap_dyn    = not bool(s.__mp['no_dyn_threshold'])

        s.__log(1, 'mmap() threshold is %ib, dyn=%s'
                % (s.__mmap_th, ['no', 'yes'][s.__mmap_dyn]))

        if s.__mmapped or s.__mmaps:
            pred = EHeap.pred(tag = EHeap.TAG_MMAPPED)

            left = s.__mmapped - sum(s.__ring.enum(pred = pred, conv = len))

            if left == 0:
                status = 'all known'

            elif left == s.__mmapped:
                status = 'all unknown'

            elif left < 0:
                status = '%s overdisq' % Humans.bytes(-left)

            else:
                status = '%s unknown' % Humans.bytes(left)

            s.__log(1, 'heap has %s in %i mmaps(), %s'
                % (Humans.bytes(s.__mmapped), s.__mmaps, status))

    def __arena_by_addr(s, at):
        for arena in s.__arena:
            if long(arena.__at__()) == long(at): return arena

    def lookup(s, at):
        proximity, rg = s.__ring.lookup(at, exact = False)

        if proximity == Ring.MATCH_EXACT:
            return s.__lookup_rg(at, rg)

        return (IHeap.REL_OUTOF, None, None, None, None)

    def enum(s, callback = None, size = None, used = True):
        ''' Walk through all of known chunks in my heap '''

        if used is True:
            return s.__enum_used(callback, size)

        elif size is not None:
            raise Exception('cannot match block size for free list')

        else:
            raise Exception('not implemented')

    def __lookup_rg(s, at, span):
        alias = span.exten().lookup(at, alias = Alias.ALIAS_BEFORE)

        s.__log(8, 'alias at 0x%x, distance=%s'
                    % (alias, Humans.bytes(at - alias)))

        for chunk in Chunk(s.__sc, alias, Chunk.TYPE_REGULAR):
            relation, offset = chunk.relation(at)

            if relation == IHeap.REL_OUTOF:
                continue

            elif span.exten().__tag__() == EHeap.TAG_MMAPPED:
                relation = IHeap.REL_HUGE

            else:
                pass # TODO: lookup fastbin slots and top chunk

            return (relation, chunk.inset(), offset) + chunk.__netto__()

    def __enum_used(s, callback = None, size = None):
        ''' Enum given type of objects in arena '''

        if size is not None: size = set(map(s.__sc.round, size))

        for span in s.__ring:
            start, end = span.__rg__()

            it = Chunk(s.__sc, start, Chunk.TYPE_REGULAR, end = end)

            for chunk in it:
                if size is not None and len(chunk) not in size:
                    continue

                if chunk.__at__() == s.__top.__at__():
                    break

                if chunk.is_used(): yield chunk
