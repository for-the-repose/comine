#__ LGPL 3.0, 2017 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from itertools          import chain, count
from comine.core.heman  import HeMan, IHeap
from comine.maps.exten  import IExten
from comine.maps.ring   import Ring
from comine.maps.tools  import Tools
from comine.heaps.pred  import _HNil
from comine.misc.humans import Humans
from comine.misc.func   import gmap

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
        s.__mask    = TheLfAlloc.PAGE - 1

        assert s.__page & s.__mask == 0

        s.__s2blo   = None  # small blocks enum, { index -> [ block ] }
        s.__b2free  = None  # small free chunks, { block -> bitmap }
        s.__intern  = set() # chunks of global free lists, [ chunk ]

        s.__index   = rvar('chunkSizeIdx')
        s.__lfree   = rvar('lbFreePtrs')
        s.__fe_tls  = rvar('pThreadInfoList')
        s.__fe_glob = rvar('globalFreeLists')
        s.__fe_page = rvar('blockFreeList')
        s.__bords   = rvar('borderSizes')

        ends = map(lambda x: s.__libc.addr(rvar(x)),
                    ['linuxAllocPointer', 'linuxAllocPointerHuge'] )

        s.__small   = (TheLfAlloc.START, ends[0])
        s.__huge    = (TheLfAlloc.HUGE, ends[1])

        s.__efblk   = 0     # block in free list isn't free
        s.__esmall  = 0     # an invalid free block addr
        s.__esize   = 0     # free block size missmatch
        s.__esame   = 0     # free list chunk duplicates
        s.__efvec   = 0     # free vec double usage

        s.__log(1, 'small rg at (%x, %x), %s'
                % (s.__small + (Humans.region(s.__small),)))

        s.__log(1, 'huge rg at (%x, %x), %s'
                % (s.__huge + (Humans.region(s.__huge),)))

        s.__traverse_size_info(rvar)
        s.__traverse_small_map()
        s.__check_free_block()

        s.__world.push(s, s.__ring, provide = 'heap')

        s.__traverse_free_small()
        s.__traverse_free_large()
        s.__traverse_large_mmap()

        s.__log(1, "bugs outof=%u nmatch=%u same=%u fvec=%u fblk=%u"
                    % (s.__esmall, s.__esize, s.__esame, s.__efvec, s.__efblk))

        s.__ready = True
        s.__show_block_stats()

    @classmethod
    def __who__(s):     return 'lfalloc'

    def __ready__(s):   return s.__ready

    def __traverse_size_info(s, rvar):
        sizes, heads = map(rvar, ['nSizeIdxToSize', 'globalCurrentPtr' ])

        def _h2info(slot):
            at = s.__libc.addr(heads[slot])

            return (s.__block_for(at), at)

        s.__heads = map(_h2info, xrange(heads.type.range()[1] + 1))
        s.__sizes = map(lambda x: int(sizes[x]),
                        xrange(sizes.type.range()[1] + 1))

        items = lambda x: int(TheLfAlloc.BLOCKS / x)
        waste = lambda x: (items(x) * x) if x > 0 else  None

        s.__waste = map(waste, s.__sizes)

        fvecb = 16 * s.__libc.std_type('ptr_t').sizeof

        s.__fvidx = s.__index_for_size(fvecb)

        if s.__fvidx is None:
            raise Exception('cannot find index for fvec %ub' % fvecb)

        s.__log(3, 'small %u buckets [%u, %u]b, fvec %ub(%ub) index=%u'
                % (len(s.__sizes) - 1, s.__sizes[1], s.__sizes[-1],
                    fvecb, s.__round(fvecb), s.__fvidx))

    def __traverse_small_map(s):
        items = s.__index.type.range()[1] + 1

        s.__s2blo = { block : [ ] for block in xrange(-1, len(s.__sizes)) }

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

        s.__log(1, "upper used block=%u at=%x"
                % (s.__upper, s.__upper * TheLfAlloc.BLOCKS))

        s.__log(1, "found %s in small %u chunks %u blocks, %s pads"
                % (Humans.bytes(total), chunks, used, Humans.bytes(waste)))

    def __show_block_stats(s):
        s.__log(8, " bucket  bytes   chunks    cfree  cnt  >0 1/4 1/2 3/4 100")
        s.__log(8, " --------------------------------------------------------")

        for index, blocks in s.__s2blo.items():
            if index > 0 and len(blocks) > 0:
                size = s.__sizes[index]
                caps = int(TheLfAlloc.BLOCKS / size)
                chunks = caps * len(blocks)

                unused, touch = 0, [ 0, 0, 0, 0, 0 ]
                _o2, _o4 = (caps >> 1), (caps >> 2)

                lvl = [ 1, _o4, _o2, _o2 + _o4, caps ]

                for num in map(lambda x: len(s.__b2free[x]), blocks):
                    unused += num
                    touch[0] += bool(num >= lvl[0])
                    touch[1] += bool(num >= lvl[1])
                    touch[2] += bool(num >= lvl[2])
                    touch[3] += bool(num >= lvl[3])
                    touch[4] += bool(num >= lvl[4])

                tlit = Humans.bytes(chunks * size)
                xlit = ' '.join(map(lambda x: '%3u' % x, touch))

                s.__log(8, "  %5u % 5s %8u %8u %4u %s"
                    % (size, tlit, chunks, unused, len(blocks), xlit))

    def __check_free_block(s):
        rvar = gdb.selected_frame().read_var

        array   = rvar('freeChunkArr')
        listed  = rvar('freeChunkCount')
        blocks  = len(s.__s2blo.get(-1, 0))

        for block in gmap(int, xrange(listed)):
            s.__efblk += 1 if int(s.__index[block]) > 0 else 0

        s.__unused = blocks * TheLfAlloc.BLOCKS

        s.__log(1, "found %s in small %u unused blocks, %u listed -%u failed"
                % (Humans.bytes(s.__unused), blocks, listed, s.__efblk))

    def __traverse_free_small(s):
        _items = lambda x: int(TheLfAlloc.BLOCKS/ x)
        _caps = lambda x: _items(s.__index[x]) if s.__index[x] > 0 else 0

        s.__b2free = [ _BMap(_caps(x)) for x in xrange(s.__upper + 1) ]

        for name in ('tls', 'glob'):
            was = s.__stat_on_free((0, 0, 0))
            func = getattr(s, '_TheLfAlloc__traverse_free_' + name)
            nums = sum(gmap(lambda x: 1, func()))
            grow = s.__stat_on_free(was)

            s.__log(1, "found +%s in free %s %u chunks %u buckets"
                        % (Humans.bytes(grow[1]), name, grow[0], nums))

            if grow[2] > 0:
                s.__log(4, 'set %s has %u error chunks' % (name, grow[2]))

        s.__traverse_free_pages(lambda x: None, s.__fe_page)

        s.__log(1, "found %s in internal %u free vecs"
                    % (Humans.bytes(128 * len(s.__intern)), len(s.__intern)))

    def __traverse_free_tls(s):
        tls = s.__fe_tls

        while s.__libc.addr(tls) != 0x0:
            for index in xrange(1, len(s.__sizes)):
                ar = tls['FreePtrs'][index]
                lv = int(tls['FreePtrIndex'][index])

                for z in xrange(lv, ar.type.range()[1] + 1):
                    s.__push_small(index, s.__libc.addr(ar[z]))

            tls = tls['pNextInfo']

            yield 1

    def __traverse_free_glob(s):
        pptr_t = s.__libc.std_type('ptr_t').pointer()

        for index in xrange(1, len(s.__sizes)):
            def _page(head):
                ar = head.cast(pptr_t)

                for x in  xrange(1, 16):
                    s.__push_small(index, s.__libc.addr(ar[x]))

            s.__traverse_free_pages(_page, s.__fe_glob[index])

            yield 1

    def __traverse_free_pages(s, push, entry):
        for head in map(lambda x: entry[x] ,('Head', 'Pending')):
            seen, start = set(), s.__libc.addr(head)

            while True:
                addr = s.__libc.addr(head)

                if addr == 0x0:
                    pass
                elif s.__index_by_addr(addr)[0] != s.__fvidx:
                    s.__log(4, 'invalid fvec 0x%x, in 0x%x' % (addr, start))
                elif addr in seen:
                    s.__log(4, 'cycled fvec at 0x%x, in 0x%x' % (addr, start))
                else:
                    push(head)

                    if addr in s.__intern:
                        s.__efvec +=1
                    else:
                        s.__intern.add(addr)

                    seen.add(addr)
                    head = head['Next']

                    continue

                break

    def __push_small(s, index, at):
        if not(s.__small[0] <= at < s.__small[1]):
            s.__esmall += 1
        else:
            block = int(at / TheLfAlloc.BLOCKS)

            if index != s.__index[block]:
                s.__esize += 1
            else:
                off = int((at % TheLfAlloc.BLOCKS) / s.__sizes[index])

                if s.__b2free[block].add(off):
                    s.__esame += 1

    def __stat_on_free(s, was):
        items, volume, failed = 0, 0, (s.__esame + s.__esmall + s.__esize)

        it = gmap(lambda x: int(s.__index[x]), xrange(s.__upper + 1))

        for bmap, sinx in zip(s.__b2free, it):
            if sinx > 0:
                items += len(bmap); volume += len(bmap) * s.__sizes[sinx]

        return (items - was[0], volume - was[1], failed - was[2])

    def __traverse_free_large(s):
        stats = [0, 0, 0] # count, bytes, exacts

        s.__log(8, 'traversing free huge maps list')

        for z in xrange(s.__lfree.type.range()[1] + 1):
            line = s.__lfree[z]

            for y in xrange(line.type.range()[1] + 1):
                at = s.__libc.addr(line[y])

                if at > 0:
                    rg = (at - s.__page, None)

                    s.__huge_block_as(rg, EHeap.TAG_FREE, stats)

        s.__log(1, "found %s in large %u free blocks"
                        % (Humans.bytes(stats[1]), stats[0]))

    def __traverse_large_mmap(s):
        stats = [0, 0, 0, 0] # count, bytes, exact, skips

        s.__log(8, 'searching for used huge maps regions')

        with s.__ring.begin(auto = True) as trans:
            walk = s.__world.physical(s.__huge, unused = s.__ring)

            for place, _ in walk:
                while place[0] < place[1]:
                    end = s.__huge_block_as(place, EHeap.TAG_MMAP, stats, trans)

                    if end is not None:
                        place = (~s.__mask & (end + s.__mask), place[1])
                    else:
                        place = (~s.__mask & (place[0] + s.__page), place[1])

                        stats[3] += 1

        waste = Humans.bytes(stats[0] * s.__page) # bytes wasted in 1st page

        s.__log(1, 'found %s in large %u (=%u) blocks, %u skips, %s pads'
                % (Humans.bytes(stats[1]), stats[0], stats[2], stats[3], waste))

    def __huge_block_as(s, rg, kind, stat = None, trans = None):
        res = s.__huge_try_decode(rg)

        if res is not None:
            at, pages, size, exact = res

            if stat is not None:
                stat[0] += 1
                stat[1] += size
                stat[2] += 1 if exact else 0

            place = (at - s.__page, at + size)
            target  = trans or s.__ring
            exten   = EHeap(tag = kind)

            target.make(place, exten = exten)

            return at + size

    def __huge_try_decode(s, rg): # -> (at, pages, bytes, exact) or None
        '''
            Hints for lare block detection:

            0. Block should be aligned at page size;

            1. Has special leading block of page size with single used
                value type of size_t, holds total pages in this map;

            2. At least 8 pages should be used, least chunks are taken
                from small blocks pool.
        '''

        psize_t = s.__libc.std_type('size_t').pointer()

        if rg[0] & s.__mask == 0 and Tools.len(rg) > 8 * s.__page:
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
                size, gran = s.__granz(index)

                item    = int((at - block * BLOCKS) / size)
                head    = s.__heads[index]

                chunk += item * size

                if head[0] == block and at >= head[1]:
                    gran, rel = None, IHeap.REL_ZERO
                elif index == s.__fvidx and chunk in s.__intern:
                    gran, rel = None, IHeap.REL_INTERN
                elif item * size >= s.__waste[index]:
                    rel, size = IHeap.REL_INTERN, BLOCKS - s.__waste[index]
                elif s.__b2free is None:
                    rel = IHeap.REL_MAYBE
                elif s.__b2free[block].__has__(item):
                    rel = IHeap.REL_FREE

            return (rel, chunk, at - chunk, size, gran)

        elif exten.__tag__() in EHeap.TAGS_HUGE:
            return s.__huge_meta(span, at)

        return (IHeap.REL_OUTOF, None, None, None, None)

    def enum(s, place = None, pred = None, huge = None):
        def _filter(it):
            for block, rg, index in it:
                is_free_item = s.__b2free[block].__has__
                size, gran = s.__granz(index)

                for item, at in zip(count(), xrange(rg[0], rg[1], size)):
                    meta = (IHeap.REL_CHUNK, at, size, gran)

                    if is_free_item(item):
                        pass
                    elif index == s.__fvidx and at in s.__intern:
                        pass
                    elif pred is None or pred(*meta):
                        yield meta

        with (pred or _HNil()).begin(s.__round) as pred:
            sizes, cond = s.__enums_rg_cond(huge)

            if pred.__prec__(rg = sizes):
                for span in s.__ring.enum(place, pred = cond):
                    exten   = span and span.exten()

                    if exten.__tag__() == EHeap.TAG_SMALL:
                        it = s.__enum_small(span.__rg__())

                        for meta in _filter(it): yield meta

                    elif exten.__tag__() == EHeap.TAG_MMAP:
                        meta = s.__huge_meta(span)

                        if not pred or pred(*meta): yield meta

    def __enum_small(s, rg):
        start, end = map(s.__block_for, (rg[0], rg[1] - 1))

        _2addr = lambda x: x * TheLfAlloc.BLOCKS

        for block in xrange(start, end + 1):
            index   = int(s.__index[block])

            if index > 0:
                head = s.__heads[index]

                if block == head[0]:
                    place = (_2addr(block), head[1])
                else:
                    place = (_2addr(block), _2addr(block + 1))

                yield block, place, index

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
        if size is not None:
            index = s.__index_for_size(size)

            if index is not None:
                return s.__sizes[index]
            else:
                size += s.__mask

                return size ^ (size & s.__mask)

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

    def __index_by_addr(s, at):
        if s.__small[0] <= at < s.__small[1]:
            block = int(at / TheLfAlloc.BLOCKS)

            return s.__index[block], block

    def __index_for_size(s, size):
        for z in xrange(0, len(s.__sizes)):
            if size <= s.__sizes[z]: return z

    def __block_for(s, at):     # -> place | None
        if s.__small[0] <= at < s.__small[1]:
            return int(at / TheLfAlloc.BLOCKS)

    def __granz(s, index):      # -> size, gran
        size    = s.__sizes[index]
        gran    = size - (index >  1 and s.__sizes[index - 1])

        return (size, gran)

    @classmethod
    def __fn_max_chunk(cls, ring, heap):
        pred    = EHeap.pred(tag = EHeap.TAGS_HUGE)
        huges   = ring.enum(pred = pred, conv = len)

        return max(chain([ heap.__sizes[-1] + 1 ], huges))


class _BMap(object):
    __slots__ = ('_BMap__caps', '_BMap__used', '_BMap__map');

    def __init__(s, caps):
        s.__caps    = (caps + 7) >> 3
        s.__used    = 0
        s.__map     = None

    def __has__(s, x):  return s.__used and s.__map[x >> 3] & (1 << (x & 0x7))

    def __len__(s):     return s.__used

    def add(s, num):
        num, mask = (num >> 3), (1 << (num & 0x7))

        if s.__used == 0: s.__map = bytearray(s.__caps)

        if not (s.__map[num] & mask):
            s.__map[num] |= mask
            s.__used += 1
        else:
            return True


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

    def __ident__(s):
        return (s.__class__.__name__, EHeap.__NAMES.get(s.__tag))

    def __args__(s, rg):
        kl, kw = IExten.__args__(s, rg)

        return ((s.__heap, s.__tag) + kl, kw)

    def extend(s, rg, force = False):
        return True

    @classmethod
    def pred(cls, tag):
        if tag is not None:
            return lambda span: span.exten().__tag__() in tag
