#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from sys        import stdout
from itertools  import count, izip
from bisect     import bisect_left

from comine.iface.heap  import IHeap
from comine.core.freg   import Freg
from comine.exun.stack  import EStack
from comine.misc.humans import Humans
from comine.misc.func   import gmap


class Walk(object):
    def __init__(s, save = None):
        s.__save    = save
        s.__seen    = 0
        s.__found   = 0
        s.__bytes   = 0
        s.__stats   = {}

    def __call__(s, lost, it):
        save = _Logger(s.__save)

        try:
            s.__traverse(lost, save, it)

        finally:
            save.close()

            s.__show_result()

    def __traverse(s, lost, save, it):
        for s.__seen, (rel, at, size, gran) in izip(count(1), it):
            if lost(at) is not True:
                s.__found   += 1
                s.__bytes   += size

                s.__stats[size] = s.__stats.get(size, 0) + 1

                rlit = IHeap.REL_NAMES.get(rel, '?%u' % rel)

                save('%6s 0x%x %ub ~%ub' % (rlit, at, size, gran))

            if s.__seen % 1000000 == 0: s.__show_result(True)

    def __show_result(s, short = False):
        bytes = Humans.bytes(s.__bytes)

        print('lost %s in %u chunks of %u'
                    % (bytes, s.__found, s.__seen))

        if not short and len(s.__stats) > 0:
            print '-- chunk size stats'

            for size, count in sorted(list(s.__stats.items())):
                bytes = Humans.bytes(size * count)

                print '   %5ub %6u %8s' % (size, count, bytes)


class Lost(object):
    ''' Lost chunks miner tool '''

    def __init__(s, heap, index, root, cache = 2 ** 16):
        s.__index   = index
        s.__heap    = heap
        s.__root    = root
        s.__lost    = set()

        s.__caret   = 0
        s.__wind    = [ None ] * cache
        s.__live    = set()

    def __call__(s, addr):
        seen, stack = set(), [ (addr, iter([(None, addr)])) ]

        while stack:
            for _, ref in stack[-1][1]:
                rel, at, _, size, gran  = s.__heap.lookup(ref)

                if rel in (IHeap.REL_OUTOF,):
                    if s.__root(ref): return s.__cache(stack)

                elif rel not in (IHeap.REL_CHUNK, IHeap.REL_HUGE):
                    pass # dead, internal heap parts

                elif at in seen:
                    pass # loop, stop deeping

                elif at in s.__lost:
                    pass # dead, already discovered

                elif at in s.__live:
                    return s.__cache(stack)

                else:
                    rg = (at, at + size)

                    stack.append((at, s.__index.lookup(rg)))

                    seen.add(at)

                    break

            else:
                stack.pop()

        s.__lost.add(addr)
        s.__lost.update(seen)

    def __cache(s, stack):
        for at, _ in filter(lambda x: x[0], stack):
            if at not in s.__live:
                s.__live.discard(s.__wind[s.__caret])

                s.__wind[s.__caret] = at
                s.__live.add(at)
                s.__caret = (s.__caret + 1) % len(s.__wind)

        return True

    @classmethod
    def terminals(cls, world):
        '''
            Builds terminal regions (roots) for addr refs:

                1. Exclude all heap discovered regions

                2. cut stack edges after sp pointer
        '''

        stack = list(world.by_prov('stack'))

        if len(stack) < 1:
            raise Exception('Cannod find stack ring')

        heap = list(world.by_prov('heap'))

        if len(heap) < 1:
            raise Exception('Cannot find heap ring')

        def _pred(span):
            if not isinstance(span.exten(), EStack):
                return True

            elif span.exten().__tag__() == EStack.TAG_FREE:
                return True

        it = world.physical(None, unused = ([heap[0], stack[0]], _pred))

        return Freg(list(map(lambda x: x[0], it)), model = world.__model__())


class _Logger(object):
    def __init__(s, path):
        if path is None:
            s.__file = None

        elif path is True:
            s.__file = stdout

        elif isinstance(path, (str, unicode)):
            s.__file = open(path, 'w')

        else:
            raise TypeError('invalid saver')

    def close(s):
        s.__file = None

    def __call__(s, ln):
        if s.__file: s.__file.write(ln + '\n')
