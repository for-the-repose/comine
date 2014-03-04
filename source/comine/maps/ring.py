#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from bisect import bisect_left, bisect_right

from comine.maps.tools  import Tools
from comine.maps.span   import Span
from comine.maps.errors import MapOfSync, MapConflict
from comine.maps.trans  import Trans
from comine.misc.humans import Humans
from comine.misc.types  import Types
from comine.misc.segen  import Segen, Scn, ScnRef

_revs = lambda rg, rev: (rg[1] - 1, rg[0] - 1, -1) if rev else rg

class Ring(object):
    ''' Collection of non-intersected map regions and alias points.

        Alias points are aggregated to regions in the ring or keeped
        out of regions (single points).
    '''

    MATCH_EXACT     = 0;    MATCH_NEAR      = 1

    __slots__ = ('_Ring__regs', '_Ring__scn', '_Ring__seg', '_Ring__by_seq')

    def __init__(s, it = None):
        s.__regs    = []
        s.__scn     = Scn()
        s.__seg     = Segen(start = 1, reuse = True)
        s.__by_seq  = {}

        if it is not None:
            for rg in it: s.make(rg)

    def __iter__(s):    return iter(s.__regs)

    def __reversed__(s): return s.enum(rev = True)

    def __len__(s):     return len(s.__regs)

    def __scn__(s):     return s.__scn.__seq__()

    def __bytes__(s):
        return reduce(lambda x, y: x + y, map(len, s.__regs), 0)

    def __repr__(s):
        _hum = Humans.bytes(s.__bytes__())

        return 'Ring(0x%x, %s %i regs, %s)' \
                    % (id(s), s.__scn, len(s), _hum)

    def bound(s, null = False):
        if len(s.__regs) > 0:
            return (s.__regs[0].__rg__()[0], s.__regs[-1].__rg__()[1])
        else:
            return None if null is True else (None, None)

    def place(s, *kl, **kw):
        return Place(s, *kl, **kw)

    def make(s, *kl, **kw):
        return s.push(Span(*kl, **kw))

    def push(s, span):
        span = Types.ensure(span, Span)

        if None in span.__rg__():
            raise Exception('cannot push wilds %s' % span)

        rg = s.__locate(span.__rg__())

        if rg[0] + 1 == rg[1] and s.__regs[rg[0]] is span:
            assert span.__ring__() == s

        if rg[0] < rg[1]:
            raise MapConflict()

        else:
            s.__regs.insert(rg[0], span)

            span._Span__bind(s, seq = s.__seg and s.__seg())

            if None not in (s.__seg, span.__seq__()):
                assert span.__seq__() not in s.__by_seq

                s.__by_seq[span.__seq__()] = span

            s.__scn.alter()

            return span

    def pop(s, span):   #   ->  self | None
        '''Remove span from ring, return self on success'''

        if span.__ring__() == s:
            rg = s.__locate(span.__rg__())

            assert rg[0] + 1 == rg[1]
            assert span == s.__regs[rg[0]]

            if None not in (s.__seg, span.__seq__()):
                s.__seg.reuse(span.__seq__())

                assert span == s.__by_seq.pop(span.__seq__(), None)

            span._Span__bind(None)

            s.__regs.pop(rg[0])
            s.__scn.alter()

            return s

    def enum(s, rg = (None, None), pred = None, conv = None, rev = False):
        used_scn = s.__scn.__seq__()

        rg = s.__locate(Tools.check(rg, True))

        pred = pred or (lambda _: True)
        conv = conv or (lambda span: span)

        for z in xrange(*_revs(rg, rev)):
            if used_scn != int(s.__scn): raise MapOfSync()

            span = s.__regs[z]

            if pred(span): yield conv(span)

    def by_seq(s, seq):     return s.__by_seq.get(seq, None)

    def lookup(s, at, exact = True):
        ''' Locate nearest region for the given address '''

        rg = s.__locate(Tools.check(at, True))

        if rg[0] + 1 < rg[1]:
            raise Exception('Cannot handle wide spans')

        elif rg[0] < rg[1]:
            return (Ring.MATCH_EXACT, s.__regs[rg[0]])

        elif exact is not True and rg[0] < len(s.__regs):
            # TODO: anaylse region egdes types
            return (Ring.MATCH_NEAR, s.__regs[rg[0]])

        else:
            return (None, None)

    def wider(s, place):
        place = Tools.check(place, True)

        rg = s.__locate(place)

        if rg[0] == rg[1]:
            pass

        elif place[0] > s.__regs[rg[0]].__rg__()[0]:
            return None

        elif place[1] < s.__regs[rg[1] - 1].__rg__()[1]:
            return None

        left  = None if rg[0] < 1 else s.__regs[rg[0] - 1].__rg__()[1]
        right = None if rg[1] >= len(s) else s.__regs[rg[1]].__rg__()[0]

        return (left, right)

    def begin(s, auto = True):
        return Trans(s, auto)

    def measure(s, call):
        was = len(s), s.__bytes__()

        call()

        after = len(s), s.__bytes__()

        return (after[0] - was[0], after[1] - was[1])

    def human_bytes(s): return Humans.bytes(s.__bytes__())

    def __index(s, at):
        return s.__regs[at]

    def __update(s, span, place):
        assert s == span.__ring__()

        if Tools.empty(span.__rg__()) is False:
            rg = s.__locate(span.__rg__())

            assert rg[0] + 1 == rg[1]
            assert s.__regs[rg[0]] == span

            if Tools.empty(place) is not False:
                s.__regs.pop(rg[0])

        s.__scn.alter()

        return True

    def __locate(s, rg):    # -> [x0, x1), intersection index range
        def _calc_l(z):
            x0 = bisect_right(s.__regs, z) - 1

            return x0 + int(x0 < 0 or z not in s.__regs[x0])

        _calc_r = lambda z: bisect_left(s.__regs, z)

        x0 = 0 if rg[0] is None else _calc_l(rg[0])

        return (x0, len(s) if rg[1] is None else _calc_r(rg[1]))


class Place(object):
    __slots__ = ('_Place__place', '_Place__ref', '_Place__rg')

    def __init__(s, ring, place = (None, None)):
        s.__place   = Tools.check(place)
        s.__ref     = ScnRef(ring, Ring)

        s.__sync(force = True)

    def __ring__(s):    return s.__ref()

    def __reversed__(s): return s.__iter__(rev = True)

    def __iter__(s, rev = False):
        s.__sync()

        for z in xrange(*_revs(s.__rg, rev)):
            s.__ref.check()

            yield s.__ref()._Ring__index(z)

    def __sync(s, force = False):
        if not s.__ref.valid(sync = True) or force:
            s.__rg = s.__ref()._Ring__locate(s.__place)
