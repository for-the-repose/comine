#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.core.logger import log
from comine.core.libc   import addr_t, ptr_t, size_t
from comine.core.heman 	import HeMan, IHeap, Heap
from comine.maps.span   import Span
from comine.maps.errors import MapOutOf
from comine.maps.ring   import Ring
from comine.maps.alias  import Alias
from comine.misc.humans	import Humans

class AnalysisError(Exception):
    ''' Internal error of analytical core, must never happen '''

class ErrorDamaged(Exception):
    ''' Unexpected data found while analysis '''

    def __init__(s, msg):
        log(1, msg)

        Exception.__init__(s)


@HeMan.register
class TheGlibcHeap(Heap):
    ''' The GLibc heap validator and data miner '''

    def __init__(s, log, mapper):
        frame   = gdb.selected_frame()

        s.__log     = log
        s.__mapper  = mapper
        s.__ready   = False

        s.__arena   = []

        s.__log(1, "building glibc arena list")

        arena = frame.read_var('main_arena')

        if arena.type.code != gdb.TYPE_CODE_STRUCT:
            raise Exception('invalid main arena symbol')

        arena_t = arena.type.pointer()

        arena = gdb.Value(arena.address).cast(arena_t)

        s.__log(1, 'primary arena at 0x%x found' % arena.cast(addr_t))

        s.__arena.append(_Arena(arena, 0, s.__log, s.__mapper))

        while True:
            arena = arena['next']

            if not s.__mapper.validate(arena.cast(addr_t)):
                raise Exception('Invalid arena links')

            if s.__arena_by_addr(arena.cast(addr_t)): break

            s.__log(1, 'secondary arena #%i at 0x%x found'
                        % (len(s.__arena), arena.cast(addr_t)))

            s.__try_to_add_arena(arena)

        s.__log(1, "heap has %i arena items" % len(s.__arena))

        s.__mp = frame.read_var('mp_')

        segment = s.__mp['sbrk_base']

        if segment.type.code != gdb.TYPE_CODE_PTR:
            raise Exception('data segment base type invalid')

        s.__examine_mmaps()
        s.__ready = True

    @classmethod
    def __who__(cls):   return 'glibc'

    def __ready__(s):   return s.__ready

    def __try_to_add_arena(s, _arena):
        try:
            arena = _Arena(_arena, len(s.__arena), s.__log, s.__mapper)

        except ErrorDamaged as E:
            s.__log(1, 'cannot add arena at 0x%x, error %s'
                        % (int(_arena.cast(addr_t)),  str(E)))

        else:
            s.__arena.append(arena)

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
            s.__log(1, 'heap has %s in %i mmaps() and it is unresolved'
                % (Humans.bytes(s.__mmapped), s.__mmaps))

    def __arena_by_addr(s, at):
        for arena in s.__arena:
            if int(arena.__at__()) == int(at): return arena

    def enum(s, *kl, **kw):
        ''' Walk through all of known chunks in my heap '''

        for arena in s.__arena:
            for chunk in arena.enum(*kl, **kw): yield chunk

    def lookup(s, at):
        for arena in s.__arena:
            result = arena.lookup(at)

            if result[0] not in (IHeap.REL_OUTOF, IHeap.REL_UNKNOWN):
                return result

        return (IHeap.REL_OUTOF, None, None, None, None)


class _Arena(object):
    FL_NON_CONTIGOUS    = 0x02

    def __init__(s, struct, seq, log, mapper):
        if struct.type.code != gdb.TYPE_CODE_PTR:
            raise TypeError('pointer to struct is needed')

        s.__log         = log
        s.__seq         = seq
        s.__primary     = (s.__seq == 0)
        s.__arena       = struct
        s.__mask        = 0
        s.__mappings    = mapper
        s.__fence       = []
        s.__map         = Ring()

        s.__sysmem  = int(s.__arena['system_mem'])
        s.__bins = s.__arena['bins']

        s.__err_out_of  = 0

        if s.__bins.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Ivalid bins member of arena')

        s.__fasts = s.__arena['fastbinsY']

        if s.__fasts.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Invalid fastbins member of arena')

        s.__remainders = s.__arena['last_remainder']

        s.__top = _Chunk(s.__arena['top'], _Chunk.TYPE_REGULAR)

#       if s.__top.type.code != gdb.TYPE_CODE_PTR:
#           raise Exception('Invalid top chunk member')

        _hu = Humans.bytes(len(s.__top))

        s.__log(1, 'arena #%i has top chunk at 0x%x +%s'
                % (s.__seq, s.__top.__at__(), _hu))

        if s.__seq == 0:
            s.__check_data_segment()
        else:
            s.__check_arena_heap()

        s.__mask    = []

        mask    = s.__arena['binmap']

        if mask.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Invalid unused bins mask type')

        for x in xrange(*mask.type.range()):
            s.__mask.append(int(mask[x]))

        s.__check_fasts()
        s.__check_bins()

        if s.__err_out_of > 0:
            s.__log(1, '%i aliases out of wild of arena #%i'
                        %(s.__err_out_of, s.__seq))

        s.__curb_the_wild()

        _dif = s.__sysmem - s.__map.__bytes__()

        s.__log(1, 'arena #%i has at most of %s unresolved data'
                % (s.__seq, Humans.bytes(_dif)))

    def __at__(s): return int(s.__arena.cast(addr_t))

    def __check_data_segment(s):
        ''' Check primary arena layed out on data segment '''

        frame   = gdb.selected_frame()

        mp = frame.read_var('mp_')['sbrk_base']

        s.__log(1, 'data segment starts at 0x%x' % mp.cast(addr_t))

        if s.contigous():
            _a1 = int(mp.cast(addr_t)) + s.__sysmem
            _a2 = s.__top.__at__() + len(s.__top)

            if _a1 != _a2:
                raise Exception('invalid main arena')

            s.__wild = Span(rg = (int(mp.cast(addr_t)), _a1), exten = Alias())

            s.__log(1, 'main arena has contigous wild at 0x%x %s'
                    % (s.__wild.__rg__()[0], s.__wild.human()))

        else:
            s.__wild = Span(rg = (None, None), exten = Alias())
            s.__base_seg = int(mp.cast(addr_t))

            s.__log(1, 'arena #%i has a scattered wild' % s.__seq)

    def __check_arena_heap(s):
        ''' Check secondaty heap arenas. It is always contogus '''

        heap_t = gdb.lookup_type('struct _heap_info').pointer()

        heap = s.__arena.cast(heap_t) - 1

        if heap['ar_ptr'] != s.__arena:
            raise ErrorDamaged(
                'invalid heap #%i arena ref=0x%x'
                        % (s.__seq, int(heap['ar_ptr'])))

        low = _Chunk.align((s.__arena + 1).cast(addr_t))
        end = int(heap.cast(addr_t)) + heap['size']

        if not (low <= s.__top.__at__() < end):
            raise ErrorDamaged('heap #%i has out of top' % s.__seq)

        end = min(s.__top.__at__() + len(s.__top), end)

        s.__wild = Span(rg = (low, end), exten = Alias())

        s.__log(1, 'Arena #%i has wild at 0x%x %s'
                    % (s.__seq, s.__wild.__rg__()[0], s.__wild.human()))

    def __check_fasts(s):
        _rg = s.__fasts.type.range()

        chunks, _bytes = 0, 0

        for x in xrange(*_rg):
            if s.__fasts[x] == 0x0: continue

            first = _Chunk(s.__fasts[x], _Chunk.TYPE_FAST, _arena = s)

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
        _rg = list(s.__bins.type.range()) + [2]

        if not (_rg[1] & 0x01):
            raise Exception('Invalid bins array size')

        for x in xrange(*_rg):
            if s.__bins[x] == s.__bins[x+1]: continue

            if validate is not False:
                if not s.__mappings.validate(s.__bins[x].cast(addr_t)):
                    raise Exception('invalid bin list head')

                if not s.__mappings.validate(s.__bins[x+1].cast(addr_t)):
                    raise Exception('invalid bin list head')

            first = _Chunk(s.__bins[x], _Chunk.TYPE_BIN, _arena = s,
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

        alias = s.__wild.exten(Alias)

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

        while len(s.__fence) > 0:
            a, b = s.__wild.__rg__()[0], s.__fence[0]

            if a >= b: raise AnalysisError('DUNNO')

            _, _, chunk = s.__traverse_right(a, b)

            if chunk.__at__() == b: s.__fence.pop(0)

            span = s.__wild.cut(chunk.__at__(), keep = Span.KEEP_AFTER)

            if span is None or len(span) == 0: break

            s.__map.push(span)

            if s.__wild.__len__() < 1: break

            at = alias.lookup(chunk.__at__(), alias = Alias.ALIAS_AFTER)

            if at is not None:
                s.__wild.cut(at, keep = Span.KEEP_AFTER)

            else:
                raise AnalysisError('no alias points before fence')

        s.__log(1, 'found %s in %i fragments' %
                    (s.__map.human_bytes(), len(s.__map)))

        if s.__wild.__len__() > 0:
            raise AnalysisError('the wild %s was not exhausted' % s.__wild)

    def __traverse_right(s, start, end, at = None):
        ''' Traverse chunks from left to right untill of fence point
            or end chunk reaching. Optional at address may be given,
            in that case travese stops at chunk where at address falls
            to and relation of at in this chunk returned.
        '''

        for chunk in _Chunk(start, _Chunk.TYPE_REGULAR, end = end):
            if at is not None:
                relation, offset = chunk.relation(at)

                if relation != IHeap.REL_OUTOF:
                    return (relation, offset, chunk)
        else:
            return (None, None, chunk)

    def __traverse_left(s, rg, at = None):
        ''' Try to resolve range at left from an alias point. There is
            no way to traverse exactly chunks from right to left. Some
            heruistic logic must be used here to find candidates for
            left continuations. This hints may be useful:

            1. All chunks are aligned to _Chunk.OFFSET value - two
                pointers, thus 0x3 for 32bit space and 0x7 for x86_64.

            2. For fragments allocated by mmap() in fallback mode exists
                minimum size and it is equal to 1mb.

            3. The beginning of allocated region by mmap() probably would
                be aligned by page size, typical is 4kb, recorded in the
                heap.

            4. Chunks in left continuation all must be marked used as
                all free chunks are known from bin lists and it is
                already accounted as heap known regions.

            5. Only chunks of primary arena may be founded in continuations
                since all secondary arenas is contigous and w/o any holes.
        '''

        last    = rg.__rg__()[0]
        nodes   = { last: [] }
        end     = rg.__rg__()[0] - 1024 * 1024

        fmask = _Chunk.FL_MMAPPED | _Chunk.FL_NON_MAIN_ARENA

        for caret in _Chunk(rg.__rg__()[0], _Chunk.TYPE_LEFT, end = end):
            probe = caret.__at__()

            if last - probe > 1024*1024: break

            if caret.flag(fmask):       continue

            if len(caret) > 1024*1024:  continue

            links = nodes.get(probe + len(caret))

            if links is not None:
                links.append(probe)

                nodes[probe] = []
                last = probe

        left = s.__resolve_left(rg.__rg__()[0], nodes)

        if left < rg.__rg__()[0]:
            rg.extend(where = -1, to = left, tag = Span.TAG_MOST)

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

    def contigous(s):
        return not (s.__arena['flags'] & _Arena.FL_NON_CONTIGOUS)

    def lookup(s, at):
        proximity, rg = s.__map.lookup(at, exact = False)

        if proximity == Ring.MATCH_NEAR:
            s.__log(1, 'try traverse left rg=' + str(rg))

            s.__traverse_left(rg)

            if rg.intersects(at):
                return s.__lookup_rg(at, rg)
            else:
                s.__log(1, 'left traverse gave nothing')

        elif proximity == Ring.MATCH_EXACT:
            return s.__lookup_rg(at, rg)

        elif  proximity is not None:
            raise Exception('Unknown proximity=%i' % proximity)

        return (IHeap.REL_OUTOF, None, None, None, None)

    def __lookup_rg(s, at, span):
        s.__log(8, 'at falls to fragment %s of arena #%i'
                    % ('[0x%x, 0x%x)' % span.__rg__(), s.__seq))

        alias = span.exten().lookup(at, alias = Alias.ALIAS_BEFORE)

        s.__log(8, 'alias at 0x%x, distance=%s'
                    % (alias, Humans.bytes(at - alias)))

        for chunk in _Chunk(alias, _Chunk.TYPE_REGULAR):
            relation, offset = chunk.relation(at)

            if relation != IHeap.REL_OUTOF:
                # TODO: lookup fastbin slots and top chunk

                return (relation, chunk.inset(), offset) + chunk.__netto__()

    def enum(s, callback = None, size = None, used = True):
        ''' Enum given type of objects in arena '''

        if used is True:
            return s.__enum_used(callback, size)

        elif size is not None:
            raise Exception('cannot match block size for free list')

        else:
            return s.__walk_bins()

    def __enum_used(s, callback = None, size = None):
        ''' Enum given type of objects in arena '''

        if size is not None: size = set(map(_Chunk.round, size))

        for rg in s.__map:
            start, end = rg.__rg__()

            for chunk in _Chunk(start, _Chunk.TYPE_REGULAR, end = end):
                if size is not None and len(chunk) not in size:
                    continue

                if chunk.__at__() == s.__top.__at__():
                    break

                if chunk.is_used(): yield chunk


class _ErrorChunk(ErrorDamaged):
    def __init__(s, chunk, msg):
        s.chunk     = chunk
        s.msg       = msg

    def __str__(s):
        return 'chunk at 0x%x: %s' % (s.chunk.__at__(), s.msg)


class _Chunk(object):
    type_t  = None

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

    # TODO: implement smart calculation, as offset of fd_nextsize
    MIN_SIZE    = int(size_t.sizeof * 4)
    FENCE_SIZE  = int(size_t.sizeof * 2)
    OFFSET      = int(size_t.sizeof * 2)
    ALIGN       = int(size_t.sizeof * 2)
    BRUTT       = int(size_t.sizeof * 1)
    MINETT      = MIN_SIZE - BRUTT

    __attrs = ('type', 'chunk', 'end', 'queue', 'first', 'arena')

    __slots__ = tuple(map(lambda x: '_Chunk__' + x, __attrs))

    def __init__(s, raw, kind_of = None, end = None, queue = None,
                            _arena = None):
        if raw == 0x0: raise ValueError('invalid address')

        s.__locate_type()

        s.__type    = kind_of or _Chunk.TYPE_REGULAR

        if s.__type == _Chunk.TYPE_ALLOCATED:
            raw = (raw.cast(ptr_t) - _Chunk.OFFSET).cast(type_t)

            kind_of = _Chunk.TYPE_REGULAR

            raise Exception('Not ready yet')

        def _cast(v):
            return v if isinstance(v, gdb.Value) else v and gdb.Value(v)

        raw, end = map(_cast, [raw, end])

        s.__chunk   = raw.cast(_Chunk.type_t)
        s.__end     = end and end.cast(addr_t)
        s.__queue   = queue and int(queue)
        s.__first   = False
        s.__arena   = _arena

        if kind_of not in _Chunk._TYPE_BINS and queue is not None:
            raise TypeError('queue applicable for bins only')

        s.__validate__()

    def __locate_type(s):
        if _Chunk.type_t is None:
            _Chunk.type_t = gdb.lookup_type('struct malloc_chunk')
            _Chunk.type_t = _Chunk.type_t.pointer()

    def meta(s):
        ''' Return metadata about of this chunk: (body, size, used) '''

        offset = _Chunk.OFFSET

        return (s.__at__() + offset, len(s) - offset, s.is_used())

    def is_used(s):
        caret = s.clone(_Chunk.TYPE_REGULAR).__next__()

        return (caret.flag(_Chunk.FL_PREV_IN_USE) != 0)

    def clone(s, kind_of):
        return _Chunk(s.__chunk, kind_of, _arena = s.__arena)

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

        elif a < _Chunk.OFFSET:
            return (IHeap.REL_HEAD, a - _Chunk.OFFSET)

        else:
            return (IHeap.REL_CHUNK, a - _Chunk.OFFSET)

    def __repr__(s):
        return '<_Chunk at 0x%x, %x %ub ~%u>' \
                    % ((s.__chunk.cast(addr_t), s.flag(0x7)) + s.__netto__())

    def __validate__(s, fence = False):
        _min = _Chunk.FENCE_SIZE if fence else _Chunk.MIN_SIZE

        if _Chunk.csize(s.__chunk) < _min:
            raise _ErrorChunk(s, 'Invalid chunk size %ib, min=%ib'
                                    % (len(s), _min))

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

            if caret.prev() != _Chunk.csize(s.__chunk):
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

        if _Chunk.csize(s.__chunk) >= 512:
            raise Exception('Invalid size %i of fastbin chunk' % len(s))

        caret = s.clone(_Chunk.TYPE_REGULAR).__next__()

        if not caret.flag(_Chunk.FL_PREV_IN_USE):
            raise Exception('Invalid fastbin chunk')

    def __blob__(s, gdbval = False):
        ''' Return blob that holds this chunk or char pointer '''

        size = _Chunk.netto(s.__chunk)

        if gdbval is True:
            ptr = s.__chunk.cast(ptr_t) + _Chunk.OFFSET

            return (size, ptr)

        else:
            inf = gdb.selected_inferior()

            return inf.read_memory(s.__at__() + _Chunk.OFFSET, size)

    def __at__(s): return int(s.__chunk.cast(addr_t))

    def inset(s):   return s.__at__() + _Chunk.OFFSET

    def __len__(s): return _Chunk.csize(s.__chunk)

    def __netto__(s):
        size, gran = _Chunk.netto(s.__chunk), _Chunk.ALIGN

        return (size, gran if size > _Chunk.MINETT else _Chunk.MINETT)

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
            _p = s.__chunk.cast(ptr_t) + _Chunk.csize(s.__chunk)

            caret = _p.cast(_Chunk.type_t)

            if s.__end and _p.cast(addr_t) >= s.__end:
                s.__chunk = caret

                raise StopIteration('terminal chunk is reached')

            if _Chunk.csize(caret) == _Chunk.FENCE_SIZE \
                    and _Chunk.csize(s.__chunk) == _Chunk.FENCE_SIZE \
                    and (caret['size'] & _Chunk.FL_PREV_IN_USE):
                raise StopIteration('fencepoint reached')

        elif s.__type == _Chunk.TYPE_BIN:
            caret = s.__chunk['fd']

            if caret.cast(addr_t) == s.__end:
                raise StopIteration()

            if caret['bk'] != s.__chunk:
                raise Exception('Invalid bin chunk linkage')

#           if s.__queue and caret['size'] < _Chunk.csize(s.__chunk):
#               raise Exception('bin is not sorted by size')

        elif s.__type == _Chunk.TYPE_FAST:
            caret = s.__chunk['fd']

            if caret == 0x0:
                raise StopIteration()

            if s.__end and careet.cast(addr_t) == s.__end:
                raise StopIteration()

            if _Chunk.csize(caret) != len(s):
                raise Exception('Invalid fastbin chunk size')

        elif s.__type == _Chunk.TYPE_TOP:
            raise Exception('Top chunk is not iterable')

        elif s.__type == _Chunk.TYPE_LEFT:
            caret = s.__chunk
            ptr = s.__chunk.cast(ptr_t)

            while True:
                if ptr <= s.__end: raise StopIteration()

                ptr -= _Chunk.OFFSET
                caret = ptr.cast(_Chunk.type_t)

                if _Chunk.csize(caret) >= _Chunk.MIN_SIZE:
                    break

        else:
            raise Exception('Unknown chunk type=%i' % s.__type)

        s.__chunk = caret
        s.__validate__(fence = True)

        return s

    next = __next__

    def is_gap(s): return len(s) == _Chunk.FENCE_SIZE

    @classmethod
    def csize(cls, chunk):
        ''' Get brutto chunk size from passed chunk object '''

        a = int(chunk['size'].cast(size_t))

        return long(a ^ (a & 0x07))

    @classmethod
    def netto(cls, chunk):
        ''' Return potential usefu payload for chunk '''

        return _Chunk.csize(chunk) - _Chunk.BRUTT

    @classmethod
    def round(cls, size, brutto = True):
        ''' Round size to chunk size as it would allocated by heap '''

        size = _Chunk.align(max(size + _Chunk.BRUTT, _Chunk.MIN_SIZE))

        return size if brutto is True else (size - _Chunk.BRUTT)

    @classmethod
    def align(cls, size):
        ''' Align size to chunk grid, round up to 2 * size_t '''

        mask = _Chunk.ALIGN-1
        size = int(size)

        if mask & (mask + 1):
            raise Exception('invalid align mask=0x%x' % mask)

        return (size + mask) ^ ((size + mask) & mask)
