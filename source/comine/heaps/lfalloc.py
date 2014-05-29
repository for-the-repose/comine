import gdb

from itertools          import chain
from comine.core.heman  import HeMan, IHeap
from comine.maps.exten  import IExten
from comine.maps.ring   import Ring
from comine.heaps.pred  import _HNil
from comine.misc.humans import Humans

@HeMan.register
class TheLfAlloc(IHeap):
    PAGE    = 4096
    BLOCKS  = 1024 * 1024
    START   = 0x100000000
    LIMIT   = 200 * 0x100000000
    HUGE    = START + LIMIT

    def __init__(s, log, infer):
        rvar = gdb.selected_frame().read_var

        props = [ ('upper', TheLfAlloc.__fn_max_chunk, s) ]

        s.__ready   = None
        s.__log     = log
        s.__infer   = infer
        s.__libc    = infer.__libc__()
        s.__world   = infer.__world__()
        s.__ring    = Ring(props = props)

        s.__page    = TheLfAlloc.PAGE
        s.__s2blo   = None  # small blocks enum, { index -> [ block ] }
        s.__s2free  = None  # small free chunks, { index -> [ chunk ] }
        s.__intern  = set() # chunks of global free lists, [ chunk ]

        s.__index   = rvar('chunkSizeIdx')
        s.__lfree   = rvar('lbFreePtrs')

        s.__free = tuple(map(rvar,
                    [ 'pThreadInfoList', 'globalFreeLists', 'blockFreeList']))

        s.__bords   = rvar('borderSizes')

        ends = map(lambda x: s.__libc.addr(rvar(x)),
                    ['linuxAllocPointer', 'linuxAllocPointerHuge'] )

        s.__small   = (TheLfAlloc.START, ends[0])
        s.__huge    = (TheLfAlloc.HUGE, ends[1])

        s.__log(1, 'small rg at (%x, %x), %s'
                % (s.__small + (Humans.region(s.__small),)))

        s.__log(1, 'huge rg at (%x, %x), %s'
                % (s.__huge + (Humans.region(s.__huge),)))

        s.__prepare_size_info(rvar)
        s.__traverse_small_map()

        s.__world.push(s, s.__ring, provide = 'heap')

        s.__traverse_free_small()
        s.__traverse_free_large()
        s.__traverse_large_map()

        s.__ready = True

    @classmethod
    def __who__(s):     return 'lfalloc'

    def __ready__(s):   return s.__ready

    def __prepare_size_info(s, rvar):
        sizes, heads = map(rvar,
                    ['nSizeIdxToSize', 'globalCurrentPtr' ])

        s.__sizes = map(lambda x: int(sizes[x]),
                        xrange(sizes.type.range()[1] + 1))

        s.__heads = map(lambda x: s.__libc.addr(heads[x]),
                        xrange(heads.type.range()[1] + 1))

        def items(x): return int(TheLfAlloc.BLOCKS / x)

        def waste(x): return (items(x) * x) if x > 0 else  None

        s.__waste = map(waste, s.__sizes)

    def __traverse_small_map(s):
        s.__s2blo = s.__make_for_sizes(list)

        items = s.__index.type.range()[1] + 1

        size, waste, total, used, chunks, s.__upper = {}, 0, 0, 0, long(), 0

        s.__log(4, "traversing %u items of small blocks index" % items)

        last = None

        for block in xrange(items):
            index = int(s.__index[block])

            if not (-1 <= index < len(s.__sizes)):
                raise Exception('Size index is out of range')
            else:
                s.__s2blo[index].append(block)

                if index != 0: s.__upper = block

                _mulb = lambda x: x * TheLfAlloc.BLOCKS

                if bool(index == 0) is bool(last):
                    if last:
                        rg      = tuple(map(_mulb, (last, block)))
                        exten   = EHeap(s, tag = EHeap.TAG_SMALL)

                        s.__ring.make(rg, exten = exten)

                    last = block if index else None

        for index, blocks in s.__s2blo.items():
            if index > 0:
                items = int(TheLfAlloc.BLOCKS / s.__sizes[index])

                useful  = items * s.__sizes[index]
                volume  = useful * len(blocks)

                size[index] = (index, int(s.__sizes[index]), volume)

                used    += len(blocks)
                chunks  += len(blocks) * items
                total   += volume
                waste   += len(blocks) * (TheLfAlloc.BLOCKS - useful)

        s.__unused = len(s.__s2blo.get(-1, 0)) * TheLfAlloc.BLOCKS

        s.__log(1, "upper used block=%u at=%x"
                % (s.__upper, s.__upper * TheLfAlloc.BLOCKS))

        s.__log(1, "found %s in small %u blocks, %u chunks"
                % (Humans.bytes(total), used, chunks))

        s.__log(1, "%s holds in small %u unused blocks"
                % (Humans.bytes(s.__unused), len(s.__s2blo.get(-1, 0))))

        s.__log(1, "wasted %s in block paddings" % Humans.bytes(waste))

    def __traverse_free_small(s):
        s.__s2free, aglo, mixed = map(s.__make_for_sizes, (set,) * 3)

        (esmall, esize), (tls, glob, gmix) = (0, 0), s.__free

        def _push(aggr, index, at):
            if at != 0x0:
                block = int(at / TheLfAlloc.BLOCKS)

                if index is None: index = int(s.__index[block])

                if not (s.__small[0] <= at < s.__small[1]):
                    esmall += 1 # out of small range
                elif s.__index[block] != index:
                    esize += 1  # block size missmatch
                else:
                    aggr[index].add(at)

        while s.__libc.addr(tls) != 0x0:
            for index in xrange(1, len(s.__sizes)):
                ar = tls['FreePtrs'][index]
                lv = int(tls['FreePtrIndex'][index])

                for z in xrange(lv, ar.type.range()[1] + 1):
                    _push(s.__s2free, index, s.__libc.addr(ar[z]))

            tls = tls['pNextInfo']

        s.__stat_free_show(s.__s2free, 'tls')

        for index in xrange(1, len(s.__sizes)):
            s.__traverse_free_pages(_push, aglo, glob[index], index)

        s.__stat_free_show(aglo, 'glob')

        s.__traverse_free_pages(_push, mixed, gmix)

        s.__stat_free_show(mixed, 'mixed')

        for index in xrange(-1, len(s.__sizes)):
            s.__s2free[index].update(aglo[index])
            s.__s2free[index].update(mixed[index])

        s.__log(1, "intern free %u vecs in %s"
                    % (len(s.__intern), Humans.bytes(128 * len(s.__intern))))

        s.__log(1, "free chunk bugs outof=%u, nmatch=%u" % (esmall, esize))

    def __traverse_free_pages(s, push, inex, entry, index = None):
        pptr_t = s.__libc.std_type('ptr_t').pointer()

        for head in map(lambda x: entry[x] ,('Head', 'Pending')):
            while s.__libc.addr(head) != 0x0:
                s.__intern.add(s.__libc.addr(head))

                ar = head.cast(pptr_t)

                def _cast(x): return s.__libc.addr(ar[x])

                for at in map(_cast, xrange(1, 16)):
                    push(inex, index, at)

                head = head['Next']

    def __make_for_sizes(s, make):
        return dict(map(lambda x: (x, make()), xrange(-1, len(s.__sizes))))

    def __stat_free_show(s, inex, cat):
        ag = s.__stat_on_free(inex)

        s.__log(1, "free %s lists %u chunks in %s"
                    % (cat, ag[0], Humans.bytes(ag[1])))

    def __stat_on_free(s, inex):
        return reduce(lambda x, y: (x[0] + y[0], x[1] + y[1]),
                    map(lambda x: (len(x[1]), s.__sizes[x[0]] * len(x[1])),
                            inex.items()))

    def __traverse_free_large(s):
        stats = [0, 0, 0] # count, bytes, exacts

        s.__log(8, 'traversing free huge maps list')

        for z in xrange(s.__lfree.type.range()[1] + 1):
            line = s.__lfree[z]

            for y in xrange(line.type.range()[1] + 1):
                at = s.__libc.addr(line[y])

                if at > 0:
                    rg = (at - s.__page, None)

                    s.__add_huge_block_as(rg, EHeap.TAG_FREE, stats)

        s.__log(1, "found %u (%s) large blocks in free"
                        % (stats[0], Humans.bytes(stats[1])))

    def __traverse_large_map(s):
        stats = [0, 0, 0] # count, bytes, exacts

        s.__log(8, 'searching for used huge maps regions')

        with s.__ring.begin(auto = True) as trans:
            walk = s.__world.physical(s.__huge, unused = s.__ring)

            for place, spans in walk:
                s.__add_huge_block_as(place, EHeap.TAG_MMAP, stats, trans)

        s.__log(1, 'found %s in %u (=%u) huge regs blocks'
                    % (Humans.bytes(stats[1]), stats[0], stats[2]))

    def __add_huge_block_as(s, rg, kind, stat = None, trans = None):
        res = s.__try_decode_huge_block(rg)

        if res is not None:
            at, pages, size, exact = res

            if stat is not None:
                stat[0] += 1
                stat[1] += size
                stat[2] += 1 if exact else 0

            place = (at - s.__page, at + size)
            target  = trans or s.__ring
            exten   = EHeap(tag = kind)

            return target.make(place, exten = exten)

    def __try_decode_huge_block(s, rg): # -> (at, pages, bytes, exact) or None
        '''
            Hints for lare block detection:

            0. Block should be aligned at page size;

            1. Has special leading block of page size with single used
                value type of size_t, holds total pages in this map;

            2. At least 8 pages should be used, least chunks are taken
                from small blocks pool.
        '''

        psize_t = s.__libc.std_type('size_t').pointer()

        if rg[0] & (s.__page - 1) == 0:
            pages = int(gdb.Value(rg[0]).cast(psize_t).dereference())

            if pages > 8:
                capacity = int(((rg[1] or s.__huge[1]) - rg[0]) / s.__page)

                if capacity - pages > 0:
                    exact = None if rg[1] is None else (capacity - pages == 1)

                    return (rg[0] + s.__page, pages, pages * s.__page, exact)

    def lookup(s, at):  # -> (rel, aligned, offset, size)
        span    = s.__ring.lookup(at)[1]
        exten   = span and span.exten()

        if exten is None:
            pass
        elif exten.__tag__() == EHeap.TAG_SMALL:
            BLOCKS  = TheLfAlloc.BLOCKS

            rel     = IHeap.REL_CHUNK
            block   = int(at / BLOCKS)
            index   = int(s.__index[block])
            chunk   = block * BLOCKS
            size    = None
            gran    = None

            if block > s.__upper or index == 0:
                rel, size = IHeap.REL_ZERO, BLOCKS
            elif index < 0:
                rel, size = IHeap.REL_KEEP, BLOCKS
            else:
                size    = s.__sizes[index]
                item    = int((at - block * BLOCKS) / size)
                gran    = size - (index >  1 and s.__sizes[index - 1])

                chunk += item * size

                if s.__heads[index] > 0 and at >= s.__heads[index]:
                    gran, rel = None, IHeap.REL_ZERO
                elif index == 8 and chunk in s.__intern:
                    gran, rel = None, IHeap.REL_INTERN
                elif item * size >= s.__waste[index]:
                    rel, size = IHeap.REL_INTERN, BLOCKS - s.__waste[index]
                elif s.__s2free is None:
                    rel = IHeap.REL_MAYBE
                elif at in s.__s2free[index]:
                    rel = IHeap.REL_FREE

            return (rel, chunk, at - chunk, size, gran)

        elif exten.__tag__() in EHeap.TAGS_HUGE:
            return s.__huge_meta(span, at)

        return (IHeap.REL_OUTOF, None, None, None, None)

    def enum(s, place = None, pred = None, huge = None):
         with (pred or _HNil()).begin(s.__round) as pred:
            sizes, cond = s.__enums_rg_cond(huge)

            if pred.__prec__(rg = sizes):
                for span in s.__ring.enum(place, pred = cond):
                    exten   = span and span.exten()

                    if exten.__tag__() == EHeap.TAG_SMALL:
                        raise Exception('Not implemented')
                    elif exten.__tag__() == EHeap.TAG_MMAP:
                        yield s.__huge_meta(span)

    def __huge_meta(s, span, at = None):
        T2REL = { EHeap.TAG_FREE: IHeap.REL_FREE,
                    EHeap.TAG_MMAP: IHeap.REL_HUGE }

        chunk   = span.__rg__()[0] + s.__page
        size    = len(span) - s.__page
        rel     = T2REL.get(span.exten().__tag__())

        if at is None:
            return (rel, chunk, size, s.__page)

        else:
            return (rel, chunk, at - chunk, size, s.__page)

    def __round(s, size):
        for z in xrange(0, len(s.__sizes)):
            if size <= s.__sizes[z]:
                return s.__sizes[z]
        else:
            mask = s.__page - 1
            size += mask

            return size ^ (size & mask)

    def __enums_rg_cond(s, huge):
        return s.__rg_for_huge(huge), s.__ring_pred_for(huge)

    def __ring_pred_for(s, huge):
        H2TAG = { True: EHeap.TAGS_HUGE, False: (EHeap.TAG_SMALL,) }

        return EHeap.pred(H2TAG.get(huge))

    def __rg_for_huge(s, huge):
        upper = huge is False or s.__ring.prop('upper')

        if huge is True:
            return (s.__sizes[-1] + 1, upper)
        elif huge is False:
            return (0, s.__sizes[-1] + 1)
        else:
            return (0, upper)

    @classmethod
    def __fn_max_chunk(cls, ring, heap):
        pred    = EHeap.pred(tag = EHeap.TAGS_HUGE)
        huges   = ring.enum(pred = pred, conv = len)

        return max(chain([ heap.__sizes[-1] + 1 ], huges))


class EHeap(IExten):
    __slots__ = ('_EHeap__heap', '_EHeap__tag')

    TAG_SMALL   = 1 # Fragments of large span used for small blocks
    TAG_MMAP    = 2 # Allocated huge block with single mmap() call
    TAG_FREE    = 3 #

    TAGS_HUGE = (TAG_MMAP, TAG_FREE)

    __NAMES = {
            TAG_SMALL:      'small',
            TAG_MMAP:       'huge',
            TAG_FREE:       'free' }

    def __init__(s, heap = None, tag = None, *kl, **kw):
        IExten.__init__(s, *kl, **kw)

        s.__tag     = tag or EHeap.TAG_BOUND
        s.__heap    = heap

    def __tag__(s):     return s.__tag

    def __hean__(s):    return s.__hean

    def __desc__(s):
        tlit    = EHeap.__NAMES.get(s.__tag, '?%u' % s.__tag)

        return 'lfalloc %s' % (tlit,)

    def __args__(s, rg):
        kl, kw = IExten.__args__(s, rg)

        return ((s.__heap, s.__tag) + kl, kw)

    def extend(s, rg, force = False):
        return True

    @classmethod
    def pred(cls, tag):
        return lambda span: span.exten().__tag__() in tag
