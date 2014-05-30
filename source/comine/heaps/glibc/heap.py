#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from itertools          import chain, ifilter

from comine.iface.heap  import IHeap, IPred
from comine.core.heman  import HeMan
from comine.maps.ring   import Ring
from comine.maps.alias  import Alias
from comine.misc.humans import Humans
from comine.misc.types  import Types
from comine.heaps.pred  import _HNil
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

        props = [ ('upper', TheGlibcHeap.__fn_max_chunk, s) ]

        s.__log     = log
        s.__infer   = infer
        s.__libc    = infer.__libc__()
        s.__ready   = False
        s.__ring    = Ring(props = props)
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
        s.__mmap_max    = (128 * (1 << 10), s.__mmap_th)

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

    def enum(s, place = None, pred = None, huge = None):
        pred = Types.ensure(pred, IPred, none = True)

        with (pred or _HNil()).begin(s.__sc.round) as pred:
            sizes, cond = s.__enums_rg_cond(huge)

            if pred.__prec__(rg = sizes):
                for span in s.__ring.enum(place, pred = cond):
                    mmapped = (span.exten().__tag__() == EHeap.TAG_MMAPPED)

                    rel = IHeap.REL_HUGE if mmapped else IHeap.REL_CHUNK

                    start, end = span.__rg__()

                    it = Chunk(s.__sc, start, Chunk.TYPE_REGULAR, end = end)

                    for chunk in ifilter(lambda x: x.is_used(), it):
                        meta = (rel, ) + chunk.meta()

                        if not pred or pred(*meta):
                            yield meta

    def __enums_rg_cond(s, huge):
        return s.__rg_for_huge(huge), s.__ring_pred_for(huge)

    def __ring_pred_for(s, huge):
        H2TAG = { True: EHeap.TAG_MMAPPED, False: EHeap.TAGS_SMALL }

        return EHeap.pred(H2TAG.get(huge))

    def __rg_for_huge(s, huge):
        upper = huge is False or s.__ring.prop('upper')

        if huge is True:
            return (s.__mmap_max[0], upper)

        elif huge is False:
            return (0, s.__mmap_max[1])

        else:
            return (0, upper)

    @classmethod
    def __fn_max_chunk(cls, ring, heap):
        pred    = EHeap.pred(EHeap.TAG_MMAPPED)
        huges   = ring.enum(pred = pred, conv = len)

        return max(chain([ heap.__mmap_max[1] ], huges))

