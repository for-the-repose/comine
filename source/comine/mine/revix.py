#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from itertools      import islice, count, chain
from os             import rename, unlink
from os.path        import isdir
from shutil         import move
from struct         import pack, Struct
from time           import time
from glob           import glob
from heapq          import heappush, heappop

from comine.core.logger import log
from comine.misc.humans import Humans
from comine.misc.func   import gmap, yrange
from comine.misc.perf   import Perf


class Revix(object):
    def __init__(s, infer, packs = 20000000):
        s.__infer   = infer
        s.__world   = infer.__world__()
        s.__base    = infer.__layout__().special('temp')
        s.__packs   = int(packs)

        if not isdir(s.__base):
            raise Exception("path='%s' isn't a dir" % s.__base)

        s.__emit = Emit(infer, s.__world.addrs(gran = 7).make())

    def build(s):
        parts = list(s.__collect())

        base = s.__infer.__layout__().special('cache')

        im = base + '/~reverse.index'

        _Merge(parts).do(im)

        rename(im, base + '/reverse.index')

        for path in parts: unlink(path)

    def __collect(s):
        it = gmap(lambda x: pack('>QQ', *x), s.__walk())

        for seq in count():
            piece = list(islice(it, s.__packs))

            if len(piece) < 1:
                break

            else:
                piece.sort()

                path = s.__base + '/_pack_%04x' % seq

                with open(path, 'wb', 2 ** 18) as F:
                    for blob in piece: F.write(blob)

                piece = None

                yield path

    def __walk(s, block = 2**18):
        for span in s.__spans():
            found, start = 0, time()

            for some in s.__emit(span.__rg__(), block):
                found += 1

                yield some

            log(4, 'indexed %u in %s from %s'
                        % (found, Humans.ago(start), span))

    def __spans(s):
        it = s.__world.physical(None, bins = True)

        return sorted(list(set(chain(*gmap(lambda x: x[1], it)))))


class Emit(object):
    def __init__(s, infer, pred):
        s.__infer   = infer
        s.__pred    = pred
        s.__atom    = Struct('<Q')
        s.__step    = s.__atom.size - 1

    def __call__(s, rg, block = 2**18):
        for caret in yrange(*(rg + (block - s.__step,))):
            size = min(block, rg[1] - caret)

            piece = s.__infer.readvar(caret, size, False)

            for off in xrange(0, size - s.__step):
                addr = s.__atom.unpack_from(piece, off)[0]

                if addr != 0 and s.__pred(addr):
                    yield (addr, caret + off)


class _Merge(object):
    def __init__(s, parts):
        s.__heap    = []

        for path in parts:
            head = _Thread(path)

            if head.next():
                heappush(s.__heap, head)

    def do(s, final):
        with open(final, 'wb', 2**18) as F:
            for one in s.__take(): F.write(one)

    def __take(s):
        while len(s.__heap) > 0:
            head = heappop(s.__heap)

            yield head.__val__()

            if head.next():
                heappush(s.__heap, head)


class _Thread(object):
    __PAT = Struct('>QQ')

    def __init__(s, path):
        s.__f       = open(path, 'rb')
        s.__val     = None
        s.__off     = 0
        s.__blo     = []

    def __val__(s):     return s.__val

    def __cmp__(s, ri): return cmp(s.__val, ri.__val)

    def next(s):
        while s.__f is not None:
            if s.__off >= len(s.__blo):
                s.__fill()

            else:
                s.__val = s.__blo[s.__off]

                s.__off += 1

                return True

    def __fill(s, items = 2 ** 16):
        assert s.__f is not None

        s.__blo = []

        piece = s.__f.read(items * s.__class__.__PAT.size)

        if len(piece) == 0:
            s.__f = None

        elif len(piece) % s.__class__.__PAT.size != 0:
            raise Exception('Invalid blob size=%u got' % len(piece))

        else:
            for z in xrange(0, len(piece), s.__class__.__PAT.size):
                s.__blo.append(piece[z: z + s.__class__.__PAT.size])

            s.__off = 0
