#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from os.path    import exists, isfile
from struct     import Struct
from bisect     import bisect_left
from math       import log

from comine.maps.tools  import Tools
from comine.misc.func   import yrange
from comine.cline.lib   import CFail


def Locate(infer, fail = True):
    layout = infer.__layout__()

    if layout is not None:
        cache = layout.special('cache', False)

        if cache and isfile(cache + '/reverse.index'):
            return Index(cache + '/reverse.index')

    if fail is True:
        raise CFail('reverse index is not found')


class Index(object):
    _FMT     = Struct('>QQ')

    def __init__(s, path):
        s.__map     = []
        s.__file    = open(path, 'rb')
        s.__usize   = Index._FMT.size

        s.__file.seek(0, 2)

        s.__len     = s.__file.tell() // s.__usize

        s.__file.seek(0, 0)

        s.__depth   = max(8, int(log(s.__len + 1.) / log(2.)))

    def __len__(s): return s.__len

    def __getitem__(s, at):
        if not (0 <= at < s.__len): raise IndexError()

        s.__file.seek(at * s.__usize)

        raw = s.__file.read(s.__usize)

        return Index._FMT.unpack(raw)

    def lookup(s, rg):
        rg = Tools.check(rg, True)

        a = bisect_left(s, (rg[0], 0))

        if a < s.__len:
            b = bisect_left(s, (rg[1], 0))

            for x in range(a, b): yield s[x]

    def enum(s):
        start = 0

        while start < s.__len:
            addr = s[start][0]

            for end in yrange(start + 1, min(s.__len, start + s.__depth)):
                if s[end][0] >= addr + 1: break

            else:
                end = b = bisect_left(s, (addr + 1, 0))

            yield (addr, _Place(s, (start, end)))

            start = end

    @classmethod
    def read(cls, F, offset = 0):
        csize = cls._FMT.size

        if offset: F.seek(offset * csize)

        while True:
            rec = F.read(csize)

            if not rec: break

            yield (cls._FMT.unpack(rec))

    @classmethod
    def write(cls, F, rec):
        F.write(cls._FMT.pack(*rec))


class _Place(object):
    def __init__(s, index, rg):
        s.__index   = index
        s.__rg      = rg
        s.__on      = None

    def __len__(s):     return s.__rg[1] - s.__rg[0]

    def __iter__(s):    return s

    def next(s):
        if s.__on is None:
            s.__on = s.__rg[0]

        elif s.__on >= s.__rg[1]:
            raise StopIteration()

        s.__on += 1

        return s.__index[s.__on - 1]
