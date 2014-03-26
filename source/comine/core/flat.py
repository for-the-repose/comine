#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.core.world  import Pred
from comine.maps.walk   import Walk
from comine.maps.tools  import Tools

class Flatten(object):
    def __init__(s, world):
        s.__world   = world

    def __iter__(s):
        walk = Walk(rings = s.__leaders())

        for rg, _ in walk.group((None, None), empty = True):
            wide, spans, total, empty, phys, logic = s.coverage(rg)

            place = rg if len(spans) > 0 else wide

            if place != (None, None) and total > 0:
                ph = (phys + 0.) / total
                lo = (logic + 0.) / total

                yield place, list(spans), (ph, lo)

    def coverage(s, rg):
        rings = map(lambda x: x.__ring__(), s.__world)

        acc, start, end = set(), None, None
        total, empty, phys, logic = 0, 0, 0, 0

        for rg, spans in Walk(rings).change(rg, empty = True):
            if Tools.finite(rg):
                size = rg[1] - rg[0]

                total += size

                if len(spans) < 1:
                    empty += size

                else:
                    end = rg[1]

                    if start is None:
                        start = rg[0]

                    acc.update(spans)

                    phys  += Flatten.__accum(Pred.phys,  spans, size)
                    logic += Flatten.__accum(Pred.logic, spans, size)

        return (start, end), acc, total, empty, phys, logic

    def __leaders(s):
        def _get(x):
            it = s.__world.by_prov(x)

            if len(it) == 1:
                return it[0]

            elif len(it) > 1:
                raise Exception()

        maps, core, exun = map(_get, ('maps', 'core', 'exun'))

        if maps is not None:
            return [ maps ]
        else:
            return [ core, exun ]

    @classmethod
    def __accum(cls, pred, rings, size):
        return size if any(map(pred, rings)) else 0
