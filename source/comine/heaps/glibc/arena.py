#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.iface.heap 	import IHeap
from comine.maps.errors import MapOutOf
from comine.maps.alias  import Alias
from comine.maps.span   import Span
from comine.misc.types  import Types
from comine.misc.humans import Humans
from .errors			import ErrorDamaged, AnalysisError
from .guess				import Guess
from .chunk				import Chunk
from .scale				import Scale
from .exten             import EHeap


class Arena(object):
    FL_NON_CONTIGOUS    = 0x02

    def __init__(s, sc, struct, seq, ring, log, infer):
        if struct.type.code != gdb.TYPE_CODE_PTR:
            raise TypeError('pointer to struct is needed')

        s.__log         = log
        s.__seq         = seq
        s.__primary     = (s.__seq == 0)
        s.__arena       = struct
        s.__mask        = 0
        s.__infer       = infer
        s.__libc        = infer.__libc__()
        s.__world       = infer.__world__()
        s.__fence       = []
        s.__ring        = ring
        s.__bound       = None
        s.__sc          = Types.ensure(sc, Scale)

        s.__sysmem  = int(s.__arena['system_mem'])
        s.__bins = s.__arena['bins']

        s.__err_out_of  = 0

        if s.__bins.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Ivalid bins member of arena')

        s.__fasts = s.__arena['fastbinsY']

        if s.__fasts.type.code != gdb.TYPE_CODE_ARRAY:
            raise Exception('Invalid fastbins member of arena')

        s.__remainders = s.__arena['last_remainder']

        s.__top = Chunk(s.__sc, s.__arena['top'], Chunk.TYPE_REGULAR)

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

        found = Guess(log, s.__world, ring).run('wild', s.__curb_the_wild)

        s.__log(1, 'arena #%i has at most of %s unresolved data'
                % (s.__seq, Humans.bytes(s.__sysmem - found)))

    def __at__(s):  return s.__libc.addr(s.__arena)

    def __seq__(s): return s.__seq

    def contigous(s):
        return not (s.__arena['flags'] & Arena.FL_NON_CONTIGOUS)

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

            first = Chunk(s.__sc, s.__fasts[x], Chunk.TYPE_FAST, _arena = s)

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
                if not s.__infer.validate(s.__bins[x].cast(addr_t)):
                    raise Exception('invalid bin list head')

                if not s.__infer.validate(s.__bins[x+1].cast(addr_t)):
                    raise Exception('invalid bin list head')

            first = Chunk(s.__sc, s.__bins[x], Chunk.TYPE_BIN, _arena = s,
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

        for chunk in Chunk(s.__sc, start, Chunk.TYPE_REGULAR, end = end):
            if at is not None:
                relation, offset = chunk.relation(at)

                if relation != IHeap.REL_OUTOF:
                    return (relation, offset, chunk)
        else:
            return (None, None, chunk)
