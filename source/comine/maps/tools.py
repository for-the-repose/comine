#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.misc.types  import Singleton

class _Rinf(object):
    __slots__       = tuple()
    __metaclass__   = Singleton

    def __call__(s):    return s

    def __repr__(s):    return 'Rinf'

    def __gt__(s, right):
        return not isinstance(right, _Rinf)

    def __lt__(s, right):
        return False

    def __ge__(s, right):
        return True

    def __le__(s, right):
        return isinstance(right, _Rinf)

    def __eq__(s, right):
        return isinstance(right, _Rinf)

    def __ne__(s, right):
        return not isinstance(right, _Rinf)


Rinf = _Rinf()


class Tools(object):
    LEFT = 0x01;    RIGHT = 0x02;   BOTH = LEFT | RIGHT

    @staticmethod
    def anchor(rg):
        if (None, None) == rg:
            return None

        else:
            return rg[0] if rg[0] is not None else rg[1]

    @staticmethod
    def isect(rg, by):
        if by[0] ==  by[1] != None:
            fall = rg[0] <= by[0] and _Romp.__lt__(by[0], rg[1])

            return by if fall else None

        else:
            rg = (max(by[0], rg[0]), _Romp.min(by[1], rg[1]))

            return None if rg[0] >= rg[1] else _Romp.rg(rg)

    @staticmethod
    def inside(rg, by):
        return rg[0] <= by[0] and _Romp.__le__(by[1], rg[1])

    @staticmethod
    def bound(x, rg):
        return (Tools.LEFT if x <= rg[0] else 0) \
                | (Tools.RIGHT if x +1 >= rg[1] else 0)

    @staticmethod
    def extend(rg, by, flags):
        bnd = lambda z, fl, ch: by[z] if flags & fl else ch(rg[z], by[z])
        rg = (bnd(0, Tools.LEFT, max), bnd(1, Tools.RIGHT, _Romp.min))

        return _Romp.rg(rg)

    @staticmethod
    def empty(rg):
        if rg is not None:
            if rg[0] == _Romp.make(rg[1]):
                return True

            elif rg[0] < _Romp.make(rg[1]):
                return False

    @staticmethod
    def finite(rg):
        return not(rg.count(None) or rg.count(Rinf))

    @classmethod
    def check(cls, at, expand = None):
        __RG_TYPES = (int, long, None.__class__, _Rinf)

        pred = lambda x: isinstance(x, __RG_TYPES)

        if isinstance(at, (int, long)) and isinstance(expand, bool):
            return (at, at + (1 if  expand else 0))

        elif not (isinstance(at, tuple) and len(at) == 2):
            raise ValueError('Invalid rg type=%s' % (at,))

        elif not (pred(at[0]) and pred(at[1])):
            raise ValueError('Invalid rg type=%s' % (at,))

        elif Tools.empty(at) is None:
            raise ValueError('Invalid rg values %s' % (at,))

        else:
            return at

    @staticmethod
    def str(rg, digits = 4, zero  = True):
        fmt = '%'\
                + ('0' if zero else '') \
                + ('%u' % (digits or 1)) \
                + 'x'

        if rg is None:
            return str(None)

        elif (None, None) == rg:
            return '[wild, wild)'

        elif rg[0] is None:
            return ('[wild, %s)' % fmt) % (rg[1],)

        elif rg[1] in (None, Rinf):
            return ('[%s, wild)' % fmt) % (rg[0],)

        elif rg[0] == rg[1]:
            return ('at %s' % fmt) % (rg[0],)

        else:
            return ('[%s, %s)' % (fmt, fmt)) % rg

    @staticmethod
    def len(rg):
        if rg is None:
            pass

        elif Tools.finite(rg) and rg[0] <= rg[1]:
            return rg[1] - rg[0]

        elif not Tools.finite(rg):
            return Rinf


class _Romp(object):
    @staticmethod
    def __le__(a, b):
        return _Romp.make(a) <= _Romp.make(b)

    @staticmethod
    def __lt__(a, b):
        return _Romp.make(a) < _Romp.make(b)

    @staticmethod
    def rg(rg):
        return tuple(map(_Romp.drop,  rg))

    @staticmethod
    def min(*kl):
        return _Romp.func(min, *kl)

    @staticmethod
    def func(fn, *kl):
        return fn(map(_Romp.make, kl))

    @staticmethod
    def make(val):
        return Rinf if val is None else val

    @staticmethod
    def drop(val):
        return None if isinstance(val, _Rinf) else val
