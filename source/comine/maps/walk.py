#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from itertools  import chain, count, takewhile

from comine.maps.ring   import Ring
from comine.maps.aggr   import Change, Group, Combine
from comine.maps.join   import _Join, _Tag

class Walk(_Join):
    def __init__(s, rings):
        rings   = filter(Walk.__filter, rings)

        _Join.__init__(s, Walk.__make, rings)

    def change(s, rg, pred = None, isect = False, *kl, **kw):
        cuts = 2 if isect else 1

        for it in s(Change(cuts = cuts, *kl, **kw), rg, pred): yield it

    def group(s, rg, pred = None, isect = False, *kl, **kw):
        cuts = 2 if isect else 1

        for it in s(Group(*kl, cuts = cuts, **kw), rg, pred): yield it

    def order(s, rg = None, pred = None):
        for rg, spans in s.group(rg, pred = pred):
            for span in spans: yield span

    @classmethod
    def __make(cls, rg, ring):
        return iter(ring.place(rg))

    @classmethod
    def __filter(cls, ring):
        if not isinstance(ring, Ring):
            raise TypeError('only Rings() supported')

        return True


class Diff(object):
    YIELD_NONE  = 0x00  # an empty match
    YIELD_ONE   = 0x01  # only in first set
    YIELD_TWO   = 0x02  # only in second set
    YIELD_ISECT = 0x04  # only common parts

    YIELD_ANY   = YIELD_ONE | YIELD_TWO
    YIELD_ALL   = YIELD_ONE | YIELD_TWO | YIELD_ISECT

    __SIDE2FL = (YIELD_ONE, YIELD_TWO)

    __slots__ = ('_Diff__sides', )

    def __init__(s, one, two):
        def _make(tag, args):
            if not isinstance(args, tuple):
                args = (args, )

            if not isinstance(args[0], Walk):
                args = (Walk(args[0]),) + args[1:]

            return (tag,) + args

        s.__sides = [ _make(0, one), _make(1, two) ]

    def __call__(s, rg, empty = False, what = YIELD_ALL):
        it = lambda rg, args: Diff.__make(rg, empty, *args)

        plex = _Join(it, s.__sides)

        for rg, sides in plex(Change(False, False), rg):
            flags, first, second = Diff.__demangle(sides)

            if flags & what or (not flags and empty):
                yield (rg, first, second)

    @classmethod
    def __make(cls, rg, empty, tag, walk, *kl):
        for place, spans in walk(Change(empty, False), rg, *kl):
            yield _Tag(tag, place, spans)

    @classmethod
    def __demangle(cls, sides):
        flags, vec = 0, [ None, None ]

        for side in sides:
            vec[side.__tag__()] = side.__me__()

            flags |= cls.__SIDE2FL[side.__tag__()]

        if flags == cls.YIELD_ANY: flags = cls.YIELD_ISECT

        return flags, vec[0], vec[1]


class OneBy(object):
    __slots__ = ('_OneBy__diff', )

    __M2WHAT = { True: Diff.YIELD_ISECT,
                 False: Diff.YIELD_ONE }

    def __init__(s, one, two):
        s.__diff = Diff(one, two)

    def __call__(s, rg, mode = True):
        aggr = Combine()
        end  = ((None, None), None, None)
        what = OneBy.__M2WHAT.get(mode)

        it = chain(s.__diff(rg, what = what), [ end ])

        for place, one, two in it:
            for pair in aggr(place, one): yield pair


class Glide(object):
    __slots__ = ('_Glide__walk', )

    def __init__(s, walk):
        s.__walk    = walk

    def __call__(s, rg, score, **kw):
        place, last = None, None

        for rg, spans in s.__walk.change(rg, empty = True, **kw):
            spans = s.__best(spans, score)

            if last in spans:
                place = (place[0], rg[1])

            else:
                if place:
                    yield place, last

                last = spans[0] if spans else None

                place = rg

        if last is not None:
            yield place, last

    def __best(s, spans, score):
        if len(spans) < 2:
            return spans

        else:
            spans = map(lambda x: (score(x), x), spans)

            spans.sort(key = lambda x: x[0])

            cuts = spans[0][0]

            go = takewhile(lambda x: x[0] <= cuts, spans)

            return list(map(lambda x: x[1], go))


class Delay(object):
    __slots__ = ('_Delay__iter', '_Delay__keep', '_Delay__more')

    def __init__(s, it, delay = 2):
        s.__iter    = iter(it)
        s.__keep    = map(lambda x: x[1], zip(count(delay), s.__iter))

        if len(s.__keep) == 0:
            s.__more = None

        elif len(s.__keep) == 1:
            s.__more = False

        else:
            s.__more = True

    def __nonzero__(s): return s.__more is not None

    def __more__(s):    return s.__more

    def __iter__(s):    return chain(s.__keep, s.__iter)
