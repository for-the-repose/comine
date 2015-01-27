#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.walk   import Diff
from comine.maps.tools  import Tools


class Olap(object):
    def __init__(s):
        pass

    def __call__(s, one, rings):
        diff = Diff(one = [ one ], two = rings)

        split = {}

        for rg, _, spans in diff(None, what = Diff.YIELD_ISECT):
            for span in spans:
                place = Tools.isect(rg, span.__rg__())

                if place is not None:

                    s.__accum(split, place, span)

        return sorted(split.iteritems(), key = lambda x: x[1], reverse = True)

    def __accum(s, split, place, span):
        key = span.exten().__ident__()

        size = Tools.len(place)

        split[key] = split.get(key, 0) + size
