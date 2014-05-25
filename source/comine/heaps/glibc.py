#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.core.logger import log
from comine.core.libc   import LibC
from comine.core.heman  import HeMan, IHeap
from comine.maps.span   import Span
from comine.maps.errors import MapOutOf
from comine.maps.ring   import Ring
from comine.maps.alias  import Alias
from comine.misc.humans import Humans
from comine.misc.types  import Types, Frozen
from comine.maps.tools  import Tools

class AnalysisError(Exception):
    ''' Internal error of analytical core, must never happen '''

class ErrorDamaged(Exception):
    ''' Unexpected data found while analysis '''

    def __init__(s, msg):
        log(1, msg)

        Exception.__init__(s)


@HeMan.register
class TheGlibcHeap(IHeap):
    ''' The GLibc heap validator and data miner '''

    def __init__(s, log, mapper):
        frame   = gdb.selected_frame()

        s.__log     = log
        s.__mapper  = mapper
        s.__libc    = mapper.__libc__()
        s.__ready   = False
        s.__ring    = Ring()
        s.__arena   = []
        s.__mp      = frame.read_var('mp_')

        s.__sc = _Scale(s.__libc, page = s.__disq_page_size())

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

        mapper.__world__().push(s, s.__ring, provide = 'heap')

        _Guess(log, s.__mapper.__world__(), s.__ring, sc = s.__sc)()

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
            if not s.__mapper.validate(at):
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
        return _Arena(s.__sc, _arena, seq, s.__ring, s.__log, s.__mapper)

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

        for chunk in _Chunk(s.__sc, alias, _Chunk.TYPE_REGULAR):
            relation, offset = chunk.relation(at)

            if relation == IHeap.REL_OUTOF:
                return

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

            it = _Chunk(s.__sc, start, _Chunk.TYPE_REGULAR, end = end)

            for chunk in it:
                if size is not None and len(chunk) not in size:
                    continue

                if chunk.__at__() == s.__top.__at__():
                    break

                if chunk.is_used(): yield chunk


class _Arena(object):
    FL_NON_CONTIGOUS    = 0x02

    def __init__(s, sc, struct, seq, ring, log, mapper):
        if struct.type.code != gdb.TYPE_CODE_PTR:
            raise TypeError('pointer to struct is needed')

        s.__log         = log
        s.__seq         = seq
        s.__primary     = (s.__seq == 0)
        s.__arena       = struct
        s.__mask        = 0
        s.__mapper      = mapper
        s.__libc        = mapper.__libc__()
        s.__world       = mapper.__world__()
        s.__fence       = []
        s.__ring        = ring
        s.__bound       = None
        s.__sc          = Types.ensure(sc, _Scale)

        s.__sysmem  = int(s.__arena['system_mem'])
        s.__bins = s.__arena['bins']

        s.__err_out_of  = 0

        if s.__bins.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Ivalid bins member of arena')

        s.__fasts = s.__arena['fastbinsY']

        if s.__fasts.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Invalid fastbins member of arena')

        s.__remainders = s.__arena['last_remainder']

        s.__top = _Chunk(s.__sc, s.__arena['top'], _Chunk.TYPE_REGULAR)

#       if s.__top.type.code != gdb.TYPE_CODE_PTR:
#           raise Exception('Invalid top chunk member')

        _hu = Humans.bytes(len(s.__top))

        s.__log(1, 'arena #%i has top chunk at 0x%x +%s'
                % (s.__seq, s.__top.__at__(), _hu))

        if s.__seq == 0:
            s.__check_data_segment()
        else:
            s.__check_arena_heap()

        s.__check_mask()
        s.__check_fasts()
        s.__check_bins()

        if s.__err_out_of > 0:
            s.__log(1, '%i aliases out of wild of arena #%i'
                        %(s.__err_out_of, s.__seq))

        found = _Guess(log, s.__world, ring).run('wild', s.__curb_the_wild)

        s.__log(1, 'arena #%i has at most of %s unresolved data'
                % (s.__seq, Humans.bytes(s.__sysmem - found)))

    def __at__(s):  return s.__libc.addr(s.__arena)

    def __seq__(s): return s.__seq

    def contigous(s):
        return not (s.__arena['flags'] & _Arena.FL_NON_CONTIGOUS)

    def __check_data_segment(s):
        ''' Check primary arena layed out on data segment '''

        frame   = gdb.selected_frame()
        addr_t  = s.__libc.std_type('addr_t')

        mp = frame.read_var('mp_')['sbrk_base']

        s.__log(1, 'data segment starts at 0x%x' % mp.cast(addr_t))

        if s.contigous():
            _a1 = int(mp.cast(addr_t)) + s.__sysmem
            _a2 = s.__top.__at__() + len(s.__top)

            if _a1 != _a2:
                raise Exception('invalid main arena')

            exten = EHeap(arena = s, tag = EHeap.TAG_BOUND)

            s.__wild = Span(rg = (int(mp.cast(addr_t)), _a1), exten = exten)

            s.__log(1, 'main arena has contigous wild at 0x%x %s'
                    % (s.__wild.__rg__()[0], s.__wild.human()))

        else:
            exten = EHeap(arena = s, tag = EHeap.TAG_FRAG)

            s.__wild = Span(rg = (None, None), exten = exten)
            s.__base_seg = int(mp.cast(addr_t))

            s.__log(1, 'arena #%i has a scattered wild' % s.__seq)

    def __check_arena_heap(s):
        ''' Check secondaty heap arenas. It is always contogus '''

        addr_t  = s.__libc.std_type('addr_t')
        heap_t  = gdb.lookup_type('struct _heap_info').pointer()

        heap = s.__arena.cast(heap_t) - 1

        if heap['ar_ptr'] != s.__arena:
            raise ErrorDamaged(
                'invalid heap #%i arena ref=0x%x'
                        % (s.__seq, int(heap['ar_ptr'])))

        low = s.__sc.align((s.__arena + 1).cast(addr_t))
        end = int(heap.cast(addr_t)) + heap['size']

        if not (low <= s.__top.__at__() < end):
            raise ErrorDamaged('heap #%i has out of top' % s.__seq)

        end = min(s.__top.__at__() + len(s.__top), end)

        s.__wild = Span(rg = (low, end), exten = EHeap(arena = s))

        s.__log(1, 'Arena #%i has wild at 0x%x %s'
                    % (s.__seq, s.__wild.__rg__()[0], s.__wild.human()))

    def __check_mask(s):
        s.__mask    = []

        mask    = s.__arena['binmap']

        if mask.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Invalid unused bins mask type')

        for x in xrange(*mask.type.range()):
            s.__mask.append(int(mask[x]))

    def __check_fasts(s):
        _rg = s.__fasts.type.range()

        chunks, _bytes = 0, 0

        for x in xrange(*_rg):
            if s.__fasts[x] == 0x0: continue

            first = _Chunk(s.__sc, s.__fasts[x], _Chunk.TYPE_FAST, _arena = s)

            for chunk in first:
                s.__push_alias_to_wild(chunk.__at__())

                chunks += 1; _bytes += len(chunk)

        s.__log(1, 'arena #%i has %i chunks and %ib in %i fastbins'
                    % (s.__seq, chunks, _bytes, _rg[1]))

    def __check_bins(s):
        chunks, _bytes = 0, 0

        for chunk in s.__walk_bins(validate = True):
            s.__push_alias_to_wild(chunk.__at__())

            chunks += 1; _bytes += len(chunk)

        _rg = list(s.__bins.type.range()) + [2]

        _hu = Humans.bytes(_bytes)

        s.__log(1, 'arena #%i has %i chunks and %s in %i bins'
                    % (s.__seq, chunks, _hu, _rg[1] >> 1))

    def __walk_bins(s, validate = False):
        addr_t  = s.__libc.std_type('addr_t')

        _rg = list(s.__bins.type.range()) + [2]

        if not (_rg[1] & 0x01):
            raise Exception('Invalid bins array size')

        for x in xrange(*_rg):
            if s.__bins[x] == s.__bins[x+1]: continue

            if validate is not False:
                if not s.__mapper.validate(s.__bins[x].cast(addr_t)):
                    raise Exception('invalid bin list head')

                if not s.__mapper.validate(s.__bins[x+1].cast(addr_t)):
                    raise Exception('invalid bin list head')

            first = _Chunk(s.__sc, s.__bins[x], _Chunk.TYPE_BIN, _arena = s,
                            end = s.__bins[x+1], queue = x>>1)

            for chunk in first: yield chunk

    def __push_alias_to_wild(s, alias):
        try:
            s.__wild.exten().push(alias)

        except MapOutOf as E:
            s.__err_out_of += 1

    def __curb_the_wild(s):
        ''' Convert heap whe wild to formally known heap fragments.

            On the most lucky case all the wild will occupy entire data
            data segment and will be curbed at once. But for non contigous
            primary arenas (only primary arena may be scattered) the wild
            may be layed out on a number of unknown memory regions and
            formal analisys may never found them all.
        '''

        s.__log(1, 'collecting fragments for arena #%i' % s.__seq)

        alias = s.__catch_the_wild()

        while len(s.__fence) > 0:
            a, b = s.__wild.__rg__()[0], s.__fence[0]

            if a >= b: raise AnalysisError('DUNNO')

            _, _, chunk = s.__traverse_right(a, b)

            if chunk.__at__() == b: s.__fence.pop(0)

            span = s.__wild.cut(chunk.__at__(), keep = Span.KEEP_AFTER)

            if span is None or len(span) == 0: break

            s.__ring.push(span)

            if s.__wild.__len__() < 1: break

            at = alias.lookup(chunk.__at__(), alias = Alias.ALIAS_AFTER)

            if at is not None:
                s.__wild.cut(at, keep = Span.KEEP_AFTER)

            else:
                raise AnalysisError('no alias points before fence')

        if s.__wild.__len__() > 0:
            raise AnalysisError('the wild %s was not exhausted' % s.__wild)

    def __catch_the_wild(s):
        alias = s.__wild.exten()

        assert alias is not None

        alias.push(s.__top.__at__())

        s.__fence.append(s.__top.__at__() + len(s.__top))
        s.__fence.sort()

        s.__log(1, 'found %i fence points for arena #%i'
                            % (len(s.__fence), s.__seq))

        if s.__wild.ami(Span.I_AM_THE_BEAST):
            alias.push(s.__base_seg)

            s.__wild.extend(rg = alias.catch(hint = s.__fence[-1]))

        elif s.__wild.ami(Span.I_AM_A_WILD):
            raise AnalysisError('oh my god, it is a wild...')

        return alias

    def __traverse_right(s, start, end, at = None):
        ''' Traverse chunks from left to right untill of fence point
            or end chunk reaching. Optional at address may be given,
            in that case travese stops at chunk where at address falls
            to and relation of at in this chunk returned.
        '''

        for chunk in _Chunk(s.__sc, start, _Chunk.TYPE_REGULAR, end = end):
            if at is not None:
                relation, offset = chunk.relation(at)

                if relation != IHeap.REL_OUTOF:
                    return (relation, offset, chunk)
        else:
            return (None, None, chunk)


class _Guess(object):
    def __init__(s, log, world, ring, sc = None):
        s.__log     = log
        s.__world   = world
        s.__ring    = Types.ensure(ring, Ring)
        s.__sc      = Types.ensure(sc, _Scale, True)

    def __call__(s):
        it = [('left', s.__extend_lefts),
                ('mmaps', s.__search_mmaped) ]

        found = sum(map(lambda x: s.run(*x), it))

    def run(s, name, call):
        change = s.__ring.measure(call)

        s.__log(1, 'found %s in %i frags while %s disq' %
                (Humans.bytes(change[1]), change[0], name))

        return change[1]

    def __extend_lefts(s):
        '''
            Invoke left traverse procedure for each known heap block that
            is known not to be closed on left side. This code has any sense
            only for primary arena that my be not a contigous.
        '''

        if len(s.__ring) > 0: s.__extend_left_do()

    def __extend_left_do(s):
        def _extend(span):
            place = s.__ring.wider(span.__rg__()[0]-1)

            if place is not None:
                for rg, spans in s.__world.physical(place):
                    if rg[1] == place[1]: return rg, spans

            return None, None

        s.__log(8, 'try to left extends on %s' % Tools.str(s.__ring.bound()))

        with s.__ring.begin(auto = True) as trans:
            for span in s.__ring.enum(pred = EHeap.pred(EHeap.TAG_FRAG)):
                left, spans = _extend(span)

                if left is not None:
                    new = s.__traverse_left(rg = left)

                    if new is not None:
                        arena = span.exten().__arena__()

                        exten = EHeap(arena, tag = EHeap.TAG_LEFT)

                        trans.make(rg = new, exten = exten)

    def __traverse_left(s, rg):
        '''
            Try to resolve range at left from an alias point. There is
            no way to traverse exactly chunks from right to left. Some
            heruistic logic must be used here to find candidates for
            left continuations. This hints may be useful:

            1. All chunks are aligned to two _Scale.__atom__() bytes,
                thus align mask is 0x3 for 32bit space and 0x7 for x86_64.

            2. Chunks in left continuation all must be marked used as
                all free chunks are known from bin lists and it is
                already accounted as heap known regions.

            3. Only chunks of primary arena may be founded in continuations
                since all secondary arenas is contigous and w/o any holes.
        '''

        last, nodes = rg[1], { rg[1]: [] }

        fmask = _Chunk.FL_MMAPPED | _Chunk.FL_NON_MAIN_ARENA

        for caret in _Chunk(s.__sc, rg[1], _Chunk.TYPE_LEFT, end = rg[0]):
            probe = caret.__at__()

            if last - probe > 1024*1024: break

            if caret.flag(fmask):       continue

            if len(caret) > 1024*1024:  continue

            links = nodes.get(probe + len(caret))

            if links is not None:
                links.append(probe)

                nodes[probe] = []
                last = probe

        left = s.__resolve_left(rg[1], nodes)

        return (left, rg[1] )if left < rg[1] else None

    def __resolve_left(s, at, nodes):
        ''' Analyse tree build while left traverse and give estimated
            left boundary for region.
        '''

        while True:
            childs = nodes.get(at)

            if childs is None:
                raise Exception('invalid left tree')

            if len(childs) == 0:
                return at

            if len(childs) > 1:
                return at

            at = childs[0]

    def __search_mmaped(s):
        '''
            Useful hints for mmaped regions search:

            1. For fragments allocated by mmap() in fallback mode exists
                minimum size and it is equal to 1mb.

            2. The beginning of allocated region by mmap() probably would
                be aligned by page size, typical is 4kb, recorded in the
                heap.

            3. Chunks in mmaped regions must be marked as used since its
                being unmmaped on free() call and isn't collected in any
                free lists.
        '''

        with s.__ring.begin(auto = True) as trans:
            def _push(place):
                exten = EHeap(tag = EHeap.TAG_MMAPPED)

                trans.make(rg = place, exten = exten)

            for place, spans in s.__world.physical(None, unused = s.__ring):
                last, thresh = None, place[0]

                for chunk in s.__mmaped_pages(place):
                    if thresh <= chunk.__at__():
                        if last is not None: _push(last)

                        last = chunk.__rg__()

                    else:
                        last = None

                    thresh = max(thresh, (last or (0,thresh))[1])

                if last is not None: _push(last)

    def __mmaped_pages(s, place):
        page = s.__sc.__page__()

        _align = lambda x, m = page - 1: (x + m) ^ ((x + m) & m)

        if Tools.len(place) > 64 * 1024:
            for at in xrange(_align(place[0]), place[1], page):
                try:
                    chunk = _Chunk(s.__sc, at, _Chunk.TYPE_REGULAR)

                    if chunk.flag(_Chunk.FL_MMAPPED):
                        if Tools.inside(place, chunk.__rg__()):
                            yield chunk

                except _ErrorChunk as E:
                    pass


class EHeap(Alias):
    __slots__ = ('_EHeap__arena', '_EHeap__tag')

    TAG_BOUND   = 1 # Completely known full arena fragment
    TAG_FRAG    = 2 # Partially known part of arena fragment
    TAG_LEFT    = 3 # Left guessed continuation of fragment
    TAG_MMAPPED = 4 # mmap'ed guessed single allocation
    TAG_SINGLE  = 5 # isolated guessed arena fragment

    __NAMES = {
            TAG_BOUND:      'bound',
            TAG_FRAG:       'frag',
            TAG_LEFT:       'left',
            TAG_MMAPPED:    'mapped',
            TAG_SINGLE:     'single' }

    def __init__(s, arena = None, tag = None, *kl, **kw):
        Alias.__init__(s, *kl, **kw)

        s.__tag     = tag or EHeap.TAG_BOUND
        s.__arena   = arena

    def __tag__(s):     return s.__tag

    def __arena__(s):   return s.__arena

    def __desc__(s):
        tlit    = EHeap.__NAMES.get(s.__tag, '?%u' % s.__tag)
        alit    = '#%u' % s.__arena.__seq__() if s.__arena else '?'
        dlit    = Alias.__desc__(s)

        return 'arena %s, %s, %s' % (alit, tlit, dlit)

    def __args__(s, rg):
        kl, kw = Alias.__args__(s, rg)

        return ((s.__arena, s.__tag) + kl, kw)

    @classmethod
    def pred(cls, tag):
        return lambda span: span.exten().__tag__() == tag


class _ErrorChunk(ErrorDamaged):
    def __init__(s, chunk, msg):
        s.chunk     = chunk
        s.msg       = msg

    def __str__(s):
        return 'chunk at 0x%x: %s' % (s.chunk.__at__(), s.msg)


class _Chunk(object):
    FL_PREV_IN_USE      = 0x1
    FL_MMAPPED          = 0x2
    FL_NON_MAIN_ARENA   = 0x4

    TYPE_DEFAULT        = 0
    TYPE_REGULAR        = 1
    TYPE_ALLOCATED      = 2
    TYPE_TOP            = 3
    TYPE_BIN            = 4
    TYPE_FAST           = 5
    TYPE_LEFT           = 6

    _TYPE_BINS = (TYPE_BIN, TYPE_FAST)

    __attrs = ('sc', 'type', 'chunk', 'end', 'queue', 'first', 'arena')

    __slots__ = tuple(map(lambda x: '_Chunk__' + x, __attrs))

    def __init__(s, me, raw, kind_of = None, end = None,
                        queue = None, _arena = None):
        if raw == 0x0: raise ValueError('invalid address')

        s.__sc      = Types.ensure(me, _Scale)
        s.__type    = kind_of or _Chunk.TYPE_REGULAR

        if s.__type == _Chunk.TYPE_ALLOCATED:
            raw     = s.__sc.begin(raw)
            kind_of = _Chunk.TYPE_REGULAR

            raise Exception('Not ready yet')

        def _cast(v):
            return v if isinstance(v, gdb.Value) else v and gdb.Value(v)

        raw, end = map(_cast, [raw, end])

        s.__chunk   = raw.cast(s.__sc.type_t)
        s.__end     = end and s.__sc.at(end)
        s.__queue   = queue and int(queue)
        s.__first   = False
        s.__arena   = _arena

        if kind_of not in _Chunk._TYPE_BINS and queue is not None:
            raise TypeError('queue applicable for bins only')

        s.__validate__()

    def meta(s):
        ''' Return metadata about of this chunk: (body, size, used) '''

        offset = s.__sc.OFFSET

        return (s.__at__() + offset, len(s) - offset, s.is_used())

    def is_used(s):
        caret = s.clone(_Chunk.TYPE_REGULAR).__next__()

        return (caret.flag(_Chunk.FL_PREV_IN_USE) != 0)

    def clone(s, kind_of):
        return _Chunk(s.__sc, s.__chunk, kind_of, _arena = s.__arena)

    def flag(s, flag): return s.__chunk['size'] & (flag & 0x7)

    def prev(s): return int(s.__chunk['prev_size'])

    def arena(s):
        if s.__chunk['size'] & _Chunk.FL_NON_MAIN_ARENA:
            pass

    def relation(s, at):
        ''' Give relation of given address to this chunk '''

        a = int(at - s.__at__())

        if not (0 <= a < len(s)):
            return (IHeap.REL_OUTOF, a)

        elif a < s.__sc.OFFSET:
            return (IHeap.REL_HEAD, a - s.__sc.OFFSET)

        else:
            return (IHeap.REL_CHUNK, a - s.__sc.OFFSET)

    def __repr__(s):
        return '<_Chunk at 0x%x, %x %ub ~%u>' \
                    % ((s.__sc.at(s.__chunk),
                            s.flag(0x7)) + s.__netto__())

    def __validate__(s, fence = False):
        if not s.__sc.fits(s.__chunk, fence):
            raise _ErrorChunk(s, 'Invalid chunk size %ib' % len(s))

        if s.__type == _Chunk.TYPE_REGULAR: s.__validate_regular()
        elif s.__type == _Chunk.TYPE_TOP:   s.__validate_top()
        elif s.__type == _Chunk.TYPE_BIN:   s.__validate_bin()
        elif s.__type == _Chunk.TYPE_FAST:  s.__validate_fast()

    def __validate_regular(s):
        ''' Regular chunks in heap have restrictions to size, above of
            mmap_thresholds chunks are allocated out of heap segemtns
            and must not be presented in any of chains.
        '''

    def __validate_top(s):
        ''' Chunk before the top is always allocated chunk'''

        if not(s.__chunk['size'] & _Chunk.FL_PREV_IN_USE):
            raise Exception('Invalid top chunk')

    def __validate_bin(s):
        ''' Restrictions applyed to chunks in bins queue:
            1. always surrounded by allocated chunks,
            2. sorted by size on asc except zero bin
        '''

        if s.__queue > 0 or s.__queue is None:
            if not(s.__chunk['size'] & _Chunk.FL_PREV_IN_USE):
                raise Exception('Invalid bin chunk')

            caret = s.clone(_Chunk.TYPE_REGULAR).__next__()

            if caret.flag(_Chunk.FL_PREV_IN_USE):
                raise Exception('Invalid bin chunk')

            if caret.prev() != s.__sc.csize(s.__chunk):
                raise Exception('Invalid bin cunk')

            try:
                caret.__next__()

            except StopIteration as E:
                log(8, 'found fence at 0x%x' % caret.__at__())

                if s.__arena is not None:
                    s.__arena._Arena__fence.append(caret.__at__())

            else:
                if not caret.flag(_Chunk.FL_PREV_IN_USE):
                    raise _ErrorChunk(caret, 'Invalid bin chunk')

    def __validate_fast(s):
        ''' Chunks in fastbins always marked as allocated and
            special restrictions to its size are applied
        '''

        if s.__sc.csize(s.__chunk) >= 512:
            raise Exception('Invalid size %i of fastbin chunk' % len(s))

        caret = s.clone(_Chunk.TYPE_REGULAR).__next__()

        if not caret.flag(_Chunk.FL_PREV_IN_USE):
            raise Exception('Invalid fastbin chunk')

    def __blob__(s, gdbval = False):
        ''' Return blob that holds this chunk or char pointer '''

        size = s.__sc.netto(s.__chunk)[0]

        if gdbval is True:
            return (size, s.__sc.inset(s.__chunk))

        else:
            inf = gdb.selected_inferior()

            return inf.read_memory(s.__at__() + s.__sc.OFFSET, size)

    def __at__(s):      return s.__sc.at(s.__chunk)

    def __rg__(s):      return (s.__at__(), s.__at__() + len(s))

    def inset(s):       return s.__at__() + s.__sc.OFFSET

    def __len__(s):     return s.__sc.csize(s.__chunk)

    def __netto__(s):   return s.__sc.netto(s.__chunk)

    def __eq__(s, chunk):
        if isinstance(chunk, _Chunk):
            return s.__at__() == chunk.__at__()
        else:
            raise TypeError('can compare only thin chunk')

    def __iter__(s):
        if s.__end is None and s.__type in (_Chunk.TYPE_LEFT, _Chunk.TYPE_BIN):
            raise Exception('end point must be set for type=%i'% s.__type)

        if s.__type != _Chunk.TYPE_LEFT:
            s.__first = True

        return s

    def __next__(s):
        if s.__first is True:
            s.__first = False

            return s

        elif s.__type == _Chunk.TYPE_REGULAR:
            _p = s.__sc.next(s.__chunk)
            caret = _p.cast(s.__sc.type_t)

            if s.__end and s.__sc.at(_p) >= s.__end:
                s.__chunk = caret

                raise StopIteration('terminal chunk is reached')

            if s.__sc.fence(s.__chunk) and s.__sc.fence(caret, True):
                raise StopIteration('fencepoint reached')

        elif s.__type == _Chunk.TYPE_BIN:
            caret = s.__chunk['fd']

            if s.__sc.at(caret) == s.__end:
                raise StopIteration()

            if caret['bk'] != s.__chunk:
                raise Exception('Invalid bin chunk linkage')

#           if s.__queue and caret['size'] < s.__sc.csize(s.__chunk):
#               raise Exception('bin is not sorted by size')

        elif s.__type == _Chunk.TYPE_FAST:
            caret = s.__chunk['fd']

            if caret == 0x0:
                raise StopIteration()

            if s.__end and s.__sc.at(caret) == s.__end:
                raise StopIteration()

            if s.__sc.csize(caret) != len(s):
                raise Exception('Invalid fastbin chunk size')

        elif s.__type == _Chunk.TYPE_TOP:
            raise Exception('Top chunk is not iterable')

        elif s.__type == _Chunk.TYPE_LEFT:
            caret = s.__chunk
            ptr = s.__chunk.cast(s.__sc.ptr_t)

            while True:
                if ptr <= s.__end: raise StopIteration()

                ptr -= s.__sc.OFFSET
                caret = ptr.cast(s.__sc.type_t)

                if s.__sc.fits(caret):
                    break

        else:
            raise Exception('Unknown chunk type=%i' % s.__type)

        s.__chunk = caret
        s.__validate__(fence = True)

        return s

    next = __next__

    def is_gap(s): return s.__sc.fence(s.__chunk)


class _Scale(Frozen):
    def __init__(s, libc, page):
        s.__page    = page

        s.type_t = gdb.lookup_type('struct malloc_chunk').pointer()

        s.ptr_t     = libc.std_type('ptr_t')
        s.__addr_t  = libc.std_type('addr_t')
        s.__size_t  = libc.std_type('size_t')

        s.__atom    = int(s.__size_t.sizeof)

        assert s.__page > 4 * s.__atom

        s.__MIN     = s.__atom * 4
        s.__FENCE   = s.__atom * 2
        s.OFFSET    = s.__atom * 2
        s.__ALIGN   = s.__atom * 2
        s.__BRUTT   = s.__atom * 1
        s.__MINETT  = s.__MIN - s.__BRUTT

        s.__mask    = s.__ALIGN - 1

        if s.__mask & (s.__mask + 1):
            raise Exception('invalid align mask=0x%x' % mask)

        Frozen.__init__(s)

    def __page__(s):    return s.__page

    def __atom__(s):    return s.__atom

    def __str__(s):
        return 'Metrics(%u, page=%u)' % (s.__atom, s.__page)

    def at(s, chunk):
        ''' Convert chunk pointer to pythonic long object '''

        return long(chunk.cast(s.__addr_t))

    def begin(s, at):
        ''' Return chunk pointer by its first allocated byte '''

        return (at.cast(s.ptr_t) - s.OFFSET).cast(s.type_t)

    def inset(s, chunk):
        ''' Return pointer to first chunk interior byte '''

        return chunk.cast(s.ptr_t) + s.OFFSET

    def next(s, chunk):
        ''' Return pointer to next chunk following supplied '''

        return chunk.cast(s.ptr_t) + s.csize(chunk)

    def csize(s, chunk):
        ''' Get brutto chunk size from passed chunk object '''

        a = long(chunk['size'].cast(s.__size_t))

        return a ^ (a & 0x07)

    def fence(s, chunk, last = False):
        size = long(chunk['size'].cast(s.__size_t))

        return (long(size ^ (size & 0x07)) == s.__FENCE
                    and (not last or size & _Chunk.FL_PREV_IN_USE))

    def fits(s, chunk, fence = False):
        ''' Returns True if chunk size fits to minimal len '''

        size = s.csize(chunk)

        if size < 0:
            raise _ErrorChunk(s, 'stupid gdb cannot convert size_t')

        return size >= (s.__FENCE if fence else s.__MIN)

    def netto(s, chunk):    # -> (size, granularity)
        size = s.csize(chunk) - s.__BRUTT

        return (size, s.__ALIGN if size > s.__MINETT else s.__MINETT)

    def round(s, size, brutto = True):
        ''' Round size to chunk size as it would allocated by heap '''

        size = s.align(max(size + s.__BRUTT, s.__MIN))

        return size if brutto is True else (size - s.__BRUTT)

    def align(s, size):
        ''' Align size to chunk grid, round up to 2 * size_t '''

        size = int(size)

        return (size + s.__mask) ^ ((size + s.__mask) & s.__mask)
