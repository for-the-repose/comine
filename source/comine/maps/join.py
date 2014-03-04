#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from heapq  import heappush, heappop, heapify

from comine.misc.types  import Types
from comine.maps.tools  import Tools, _Romp


class _Join(object):
    __slots__ = ('_Join__make', '_Join__rings')

    def __init__(s, make, rings):
        s.__make    = make
        s.__rings   = rings

    def __call__(s, aggr, rg = None, pred = None):
        ''' Enums ring spans into flatten ranges space '''

        if rg is None: rg = (None, None)

        for atom in _Sel(rg, s.__rings, pred, s.__make):
            for it in aggr(*atom): yield it


class _Sel(object):
    EV_START    = True;     EV_END      = None
    EV_ADD      = 0;        EV_DEL      = 1

    __slots__ = ('_Sel__start', '_Sel__end',  '_Sel__rg')

    def __init__(s, rg, *kl, **kw):
        s.__rg      = (rg[0], _Romp.make(rg[1]))
        s.__end     = []

        s.__prepare(rg, *kl, **kw)

    def __iter__(s):    # -> (rg, event, span)
        yield s.__rg[0], _Sel.EV_START, None

        while True:
            if s.__end and (not s.__start or s.__end[0] <= s.__start[0]):
                pop, push = (s.__end, s.__start)

            elif s.__start:
                pop, push = (s.__start, s.__end)

            else:
                yield (s.__rg[1], _Sel.EV_END, None)

                break

            wrap = heappop(pop)
            right = wrap.bound(s.__rg)

            yield (right,) +  wrap.__pair__()

            if wrap.__next__():
                heappush(push, wrap)

    def __prepare(s, rg, rings, pred, make):
        wrap = lambda x: _Wrp(make(s.__rg, x), pred or (lambda x: True))

        s.__start = filter(lambda x: x.__next__(), map(wrap, rings))

        heapify(s.__start)


class _Tag(object):
    __slots__ = ('_Tag__tag', '_Tag__rg', '_Tag__spans')

    def __init__(s, tag, rg, spans):
        s.__tag     = tag
        s.__rg      = rg
        s.__spans   = spans

    def __str__(s):
        return '_Tag(%u, %s %u spans)' \
                    % (s.__tag, Tools.str(s.__rg), len(s.__spans))

    def __repr__(s):    return s.__str__()

    def __tag__(s):     return s.__tag

    def __rg__(s):      return s.__rg

    def __me__(s):      return s.__spans

    def __iter__(s):    return iter(s.__spans)

    def __cmp__(s):     assert False


class _Wrp(object):
    __slots__ = ('_Wrp__it', '_Wrp__rg', '_Wrp__span',
                    '_Wrp__side', '_Wrp__pred', '_Wrp__at')

    def __init__(s, it, pred):
        Types.reset(s)

        s.__it      = it
        s.__pred    = pred

    def __str__(s):
        return '_Wrp{%u %s, %s}' \
                    % (s.__side, Tools.str(s.__rg), s.__span)

    def __repr__(s):    return s.__str__()

    def __rg__(s):      return s.__rg

    def __pair__(s):    return (s.__side, s.__span)

    def __at__(s):      return s.__at

    def __cmp__(s, ri): return cmp(s.__at, ri.__at)

    def bound(s, rg):
        if s.__side is _Sel.EV_ADD:
            return max(rg[0], s.__at)
        else:
            return min(rg[1], s.__at)

    def __next__(s):
        if s.__side in (None, _Sel.EV_DEL):
            try:
                while True:
                    s.__span = s.__it.next()

                    if s.__pred(s.__span):
                        break

            except StopIteration as E:
                return False

            else:
                s.__rg = s.__span.__rg__()
                s.__side = _Sel.EV_ADD

        elif s.__side == _Sel.EV_ADD:
            s.__side = _Sel.EV_DEL

        else:
            raise Exception('internal error')

        at = s.__rg[s.__side]

        s.__at = at if s.__side is _Sel.EV_ADD else _Romp.make(at)

        return True


class _Right(object):
    __slots__ = ('_Right__span', '_Right__at')

    def __init__(s, rg, span = None):
        s.__span    = span
        s.__at      = _Romp.make(rg[1])

    def __span__(s):    return s.__span

    def __at__(s):      return s.__at

    def __int__(s):     return s.__at

    def __cmp__(s, ri): return cmp(s.__at, ri.__at)
