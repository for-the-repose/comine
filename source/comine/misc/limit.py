
from heapq  import heappush, heappop
from random import random, randint

class SomeOf(object):
    __slots__ = ('_SomeOf__N', '_SomeOf__over', '_SomeOf__seen')

    def __init__(s, N, over = None):
        s.__N       = N
        s.__over    = over
        s.__seen    = 0

    def __seen__(s):    return s.__seen

    def __call__(s, it):
        keep = []

        for seq, item in enumerate(it):
            if s.__over and seq > s.__over:
                break

            elif len(keep) < s.__N:
                keep.append(item)

            elif random() < (s.__N + 0.) / seq:
                keep[randint(0, s.__N -1)] = item

            s.__seen += 1

        while keep:
            yield keep.pop()


class Limit(object):
    __slots__ = ('_Limit__wrap', '_Limit__size', '_Limit__seen')

    def __init__(s, fn, size, key = lambda x: x):
        wrap = s.__wrp_by_fn(fn)

        s.__wrap    = lambda x: wrap(key, x)
        s.__size    = size
        s.__seen    = 0

    def __seen__(s):    return s.__seen

    def __wrp_by_fn(s, fn):
        if fn is min or fn == 'min':
            return _Wax

        elif fn is max or fn == 'max':
            return _Win

        else:
            raise ValueError('unknown fn=%s'% fn)

    def __call__(s, it):
        heap = []

        for item in it:
            s.__seen += 1

            if len(heap) >= s.__size:
                heappop(heap)

            heappush(heap, s.__wrap(item))

        while heap:
            yield heappop(heap).__item__()


class _Wrp(object):
    __slots__ = ('_Wrp__key', '_Wrp__item')

    def __init__(s, fkey, item):
        s.__item    = item
        s.__key     = fkey(item)

    def __item__(s):
        return s.__item


class _Win(_Wrp):
    __slots__ = tuple()

    def __cmp__(s, ri):
        return cmp(s._Wrp__key, ri._Wrp__key)


class _Wax(_Wrp):
    __slots__ = tuple()

    def __cmp__(s, ri):
         return -cmp(s._Wrp__key, ri._Wrp__key)
