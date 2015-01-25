#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from itertools          import islice, ifilter

from comine.iface.heap  import IPred
from comine.maps.tools  import Tools, _Romp

class _HNil(IPred):
    def begin(s, *kl, **kw):    return s

    def __enter__(s):           return s

    def __exit__(s, *kl, **kw): pass

    def __call__(s, *kl, **kw): return True


class HRange(IPred):
    __slots__ = ('_HRange__rg', '_HRange__ar')

    def __init__(s, rg):
        s.__rg      = rg
        s.__ar      = None

    def begin(s, align):
        assert s.__ar is None

        s.__ar = tuple(map(align, s.__rg))
        s.__rg = (s.__rg[0], _Romp.make(s.__rg[1]))

        return s

    def __enter__(s):
        assert s.__ar is not None

        return s

    def __exit__(s, Et, Ev, tb):
        s.__ar = None

    def __prec__(s, rg):
        return Tools.isect(rg, s.__ar)

    def __call__(s, rel, at, size, delta):
        return s.__rg[0] <= size < s.__rg[1]


class HOneOf(IPred):
    __slots__ = ('_HOneOf__size', '_HOneOf__align')

    def __init__(s, size):
        s.__size    = size
        s.__align   = None

    def begin(s, align):
        assert s.__align is None

        s.__align = tuple(map(align, s.__size))

        return s

    def __enter__(s):
        assert s.__align is not None

        return s

    def __exit__(s, Et, Ev, tb):
        s.__align = None

    def __prec__(s, rg):
        it = ifilter(lambda x: Tools.isect(rg, (x, x + 1)), s.__align)

        return sum(1 for _ in islice(it, 1)) > 0

    def __call__(s, rel, at, size, delta):
        return size in s.__align
