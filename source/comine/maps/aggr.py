#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from heapq  import heappush, heappop

from comine.maps.tools  import Tools, _Romp
from comine.maps.join   import _Sel, _Wrp, _Right

class _Aggr(object):
    __slots__ = ('_Aggr__empty', '_Aggr__brake', '_Aggr__cuts',
                    '_Aggr__chev', '_Aggr__last', '_view')

    def __init__(s, empty, brake, cuts, chev):
        assert cuts > 0

        s.__empty   = empty
        s.__brake   = bool(brake)
        s.__last    = False
        s.__cuts    = cuts
        s.__chev    = chev
        s._view     = set()

    def __args__(s):    return (s.__empty, s.__brake, s.__cuts)

    def __call__(s, at, event, span):   # -> [ rg, [ object ] ]
        if event is _Sel.EV_START:
            s.__last = at

        else:
            if s.__should(event):
                empty = len(s._acts) < s.__cuts

                if (not empty or s.__empty) and s.__last < at:
                    brake = type(s.__brake) in (int, long)

                    if brake and s.__brake == s.__last:
                        if not empty:
                            yield (s.__last, s.__last), []

                        s.__brake = True

                    yield (s.__last, at), [] if empty else list(s._acts)

                s.__last = at

            if event is _Sel.EV_END:
                assert 0 == len(s._view)

                return

            elif event is _Sel.EV_ADD:
                s._view.add(span)

            elif event is _Sel.EV_DEL:
                s._view.remove(span)

                if s.__brake is True and s._plane(1):
                    s.__brake = s.__last

            s._collect(event, span)

    def __should(s, event):
        trig = (len(s._view), event) in s.__chev

        return s._should(event) or trig or event is _Sel.EV_END

    def _above(s):          return s.__cuts <= len(s._view)

    def _plane(s, up):      return s.__cuts == len(s._view) + up


class Change(_Aggr):
    __slots__ = ('_acts', )

    def __init__(s, empty = False, brake = False, cuts = 1):
        _Aggr.__init__(s, empty, brake, cuts, [(cuts - 1, _Sel.EV_ADD)])

        s._acts     = s._view

    def _should(s, event):  return s._above()

    def _collect(s, event, span): pass


class Group(_Aggr):
    __slots__ = ('_acts', )

    def __init__(s, empty = False, brake = False, cuts = 1):
        chev = [ (cuts - 1, _Sel.EV_ADD), (cuts, _Sel.EV_DEL) ]

        _Aggr.__init__(s, empty, brake, cuts, chev)

        s._acts     = set()

    def _should(s, event):  return False

    def _collect(s, event, span):
        if event is _Sel.EV_ADD:
            if s._plane(0):
                s._acts = set(s._view)

            elif s._above():
                s._acts.add(span)

        elif event is _Sel.EV_DEL:
            if s._plane(1): s._acts = set()


class _Obja(object):
    @classmethod
    def push(cls, regs, place):
        if len(regs) < 1 or regs[-1][1] < place[0]:
            regs.append(place)

        elif regs[-1][1] == place[0]:
            regs[-1] = (regs[-1][0], place[1])

        else:
            assert False


class Align(object):
    ''' Object centric aggregator, -> span, [ rg ] '''

    __slots__ = ('_Align__map', '_Align__last',
                    '_Align__zero', '_Align__cuts')

    def __init__(s, zero = False, cuts = None):
        s.__map     = {}
        s.__zero    = zero
        s.__last    = False
        s.__cuts    = cuts or 1

    def __call__(s, at, event, span):   # -> [ object, [ rg ] ]
        if event is _Sel.EV_START:
            s.__last = at

        else:
            place = (s.__last, at)

            if not Tools.empty(place):
                if len(s.__map) >= s.__cuts:
                    s.__push(place)

                s.__last = at

            if event is _Sel.EV_END:
                pass

            elif event is _Sel.EV_ADD:
                s.__map[span] = []

            elif event is _Sel.EV_DEL:
                regs = s.__map.pop(span)

                if regs or s.__zero:
                    yield (span, regs)

    def __push(s, place):
        for regs in s.__map.itervalues():
            _Obja.push(regs, place)


class Combine(object):
    __slots__ = ('_Combine__view', '_Combine__gone', '_Combine__last' )

    def __init__(s):
        s.__view    = {}
        s.__gone    = []
        s.__last    = False

    def __call__(s, rg, spans):
        for span in spans or []:
            if span in s.__view:
                _Obja.push(s.__view[span], rg)

            else:
                s.__view[span] = [ rg ]

                heappush(s.__gone, _Right(span.__rg__(), span))

        while s.__gone and _Romp.__le__(s.__gone[0], _Right(rg)):
            span = heappop(s.__gone).__span__()

            yield (span, s.__view.pop(span))
