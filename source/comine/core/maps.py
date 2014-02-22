#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from bisect import bisect_left, bisect_right

from comine.misc.humans import Humans


class MapRing(object):
    ''' Collection of non-intersected map regions and alias points.

        Alias points are aggregated to regions in the ring or keeped
        out of regions (single points).
    '''

    MATCH_EXACT     = 0
    MATCH_NEAR      = 1

    def __init__(s):
        s.__regs        = []
        s.__points      = []
        s.__total       = 0

    def __iter__(s): return iter(s.__regs)

    def __len__(s): return len(s.__regs)

    def __bytes__(s):
        return reduce(lambda x, y: x + y, map(len, s.__regs), 0)

    def __repr__(s):
        _hum = Humans.bytes(s.__bytes__())

        return '<MapRing %i regs, %s>' % (len(s), _hum)

    def push(s, rg):
        ''' Add memory region to map ring '''

        if not isinstance(rg, MapRg):
            raise TypeError('only MapRg regions accepred')

        at = rg.__rg__()[0]

        k = bisect_right(s.__points, at)

        if k < len(s.__regs) and s.__regs[k].intersects(rg):
            raise ValueError('region intersects with the set')

        if k > 0 and s.__regs[k-1].intersects(rg):
            raise ValueError('region intersects with the set')

        s.__regs.insert(k, rg)
        s.__points.insert(k, at)

    def lookup(s, at, alias = None, exact = True):
        ''' Locate nearest region for the given address '''

        k = bisect_right(s.__points, at)

        if k > 0 and s.__regs[k-1].intersects(at):
            return (MapRing.MATCH_EXACT, s.__regs[k-1])

        elif exact is not True and k < len(s.__regs):
            # TODO: anaylse region egdes types
            return (MapRing.MATCH_NEAR, s.__regs[k])

        else:
            return (None, None)

    def human_bytes(s): return Humans.bytes(s.__bytes__())


class MapRgError(Exception): pass

class MapRgOutOf(MapRgError): pass


class MapRg(object):
    ''' Formal representation of contigous memory map region as [A, B).

        Each memory range bounds may have either None, exact (EXACT)
        value or set of esimations LEAST and MOST. Estimations may
        exists both or only one of them. following conditions must be
        statisfied for this estimations:

        1. MOST < LEAST for left boundary and MOST > LEAST for right.

        2. MOST boundary can only be changed forward to LEAST or in
            the direction of opposite boundary. Vice versa for LEAST.

        3. Once MOST equals to LEAST boundary tag changed to EXACT and
            futher estimation splitting is not possible.

        4. On range cutting EXACT boundary applied to both cutted
            sides and LEAST on one side connects with MOST on anoher
            cutted point.

        Thus region may have two estimation ranges - pessimistic,
        based on LEAST estimations, and optimistic, based on MOST.

        Each range can have a set of alias points strictly inside of
        current region. This points may be used to perform fast search
        inside of region. Thus each supplied alias point must point to
        a valid application unit. Alias points is used only by app.
    '''

    __slots__ = ('_MapRg__rg', '_MapRg__tags', '_MapRg__alias')

    TAG_EXACT   = 0;    TAG_LEAST   = 1;        TAG_MOST        = 2

    ALIAS_ANY   = 0;    ALIAS_BEFORE    = 1;    ALIAS_AFTER     = 2

    TAGS_DEFAULT = (TAG_EXACT, TAG_EXACT)

    I_AM_THE_BEAST  = 1;    I_AM_A_WILD     = 2

    def __init__(s, rg = (None, None), tags = None, alias = None):
        if not isinstance(rg, (tuple, list)) or len(rg) != 2:
            raise ValueError('invalid range unit')

        def _rx(x): return x if x is None else int(x)

        s.__rg      = tuple(map(_rx, rg))
        s.__tags    = tags or MapRg.TAGS_DEFAULT
        s.__alias   = sorted(alias or [])

        if not (s.__rg[0] <= s.__rg[1]):
            raise ValueError('invalid range values')

    def __len__(s): return s.__rg[1] - s.__rg[0]

    def __repr__(s):
        if (None, None) == s.__rg:
            rg = 'wild'
        elif s.__rg[0] is None:
            rg = '[wild, 0x%x)' % s.__rg[1]
        elif s.__rg[1] is None:
            rg = '[0x%x, wild)' % s.__rg[0]
        else:
            rg = ('[0x%x, 0x%x) ' % s.__rg) + s.human()

        return '<MapRg %s, %i aliases>' % (rg, len(s.__alias or []))

    def __rg__(s): return s.__rg

    def human(s):
        ''' Return string with human readable region size '''

        return 'wild' if None in s.__rg else Humans.bytes(len(s))

    def ami(s, what):
        ''' Ask me who I am '''

        if what == MapRg.I_AM_THE_BEAST:
            return (None, None) == s.__rg
        elif what == MapRg.I_AM_A_WILD:
            return None in s.__rg
        else:
            raise ValueError('invalid attribute')

    def catch(s, hint):
        ''' Found formal a wild region boundary using aliases '''

        if not s.ami(MapRg.I_AM_THE_BEAST):
            raise Exception('only the beast may be catched')

        if len(s.__alias) < 1:
            raise Exception('too low alias points to catch')

        right = max(s.__alias[-1], hint or s.__alias[-1])

        s.__rg = (s.__alias[0], right)

    def extend(s, where, to = None, tag = None):
        ''' Extend region boundary obeying boundary tags'''

#       tag = s.__tags[0 if where < 0 else 1]

#       if tag == MapRg.TAG_EXACT:
#           raise Exception('cannot extend exact boundary')

        if to is not None:
            if where < 0 and to < s.__rg[0]:
                            s.__rg = (to, s.__rg[1])
            elif where > 0 and to > s.__rg[1]:
                            s.__rg = (s.__rg[0], to)

#       if tag is not None:
#           if where < 0: s.__tags = (tag, s.__tags[1])
#           if where > 0: s.__tags = (s.__tags[0], tag)

    def drop(s, at, alias): return s.cut(at, alias, drop = True)

    def cut(s, at, alias, drop = False, none_on_zero = True):
        ''' Split region to two parts at given split point '''

        if not (s.__rg[0] <= at <= s.__rg[1]):
            raise MapRgOutOf('at 0x%x is out of range [0x%x, 0x%x)'
                                % (at, s.__rg[0], s.__rg[1]))

        if len(s) == 0 and none_on_zero: return None

        k = bisect_left(s.__alias, at)

        if alias == MapRg.ALIAS_BEFORE:
            kw = dict(rg = (s.__rg[0], at), alias = s.__alias[:k],
                        tags = (s.__tags[0], None) )

            s.__rg, s.__alias = (at, s.__rg[1]), s.__alias[k:]

        elif alias == MapRg.ALIAS_AFTER:
            kw = dict( rg = (at, s.__rg[1]), alias = s.__alias[k:],
                        tags = (None, s.__tags[1]) )

            s.__rg, s.__alias = (s.__rg[0], at), s.__alias[:k]

        else:
            raise ValueError('invalid alias type')

        if drop is False: return  MapRg(**kw)

    def glue(s, rg):
        ''' Glue with the given region, must be contogous '''

    def push(s, at, force = False):
        ''' Add alias point for given region '''

        at = int(at)

        if s.__rg[0] is not None and at < s.__rg[0]:
            raise MapRgOutOf('alias out of region')

        if s.__rg[1] is not None and at >= s.__rg[1]:
            raise MapRgOutOf('alias out of region')

        k = bisect_right(s.__alias, at)

        if k < 1 or s.__alias[k-1] != at:
            s.__alias.insert(k, at)

    def alias(s, at, alias = None, none_on_outof = False):
        ''' Found aliased point for given address '''

        if not(s.__rg[0] <= int(at) < s.__rg[1]):
            raise MapRgOutOf('Address is out of region')

        k = bisect_right(s.__alias, at)

        if 0 < k and s.__alias[k-1] == at:
            return s.__alias[k-1]

        if alias == MapRg.ALIAS_BEFORE:
            return s.__alias[k-1] if k > 0 else s.__rg[0]

        elif alias == MapRg.ALIAS_AFTER:
            return s.__alias[k] if k < len(s.__alias) else None

        else:
            raise ValueError('invalid alias value')

    def intersects(s, at):
        ''' Return True if given region is intersects with self '''

        if isinstance(at, MapRg):
            _r = at.__rg__()

            return _r[0] < s.__rg[1] and _r[1] > s.__rg[0]

        elif isinstance(at, int):
            return s.__rg[0] <= at < s.__rg[1]

        else:
            raise TypeError('invalid object type=' + type(at))
