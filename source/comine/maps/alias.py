#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from bisect import bisect_left, bisect_right

from comine.maps.tools  import Tools
from comine.maps.exten  import IExten
from comine.maps.errors import MapOutOf

class Alias(IExten):
    '''
        Each range can have a set of alias points strictly inside of
        current region. This points may be used to perform fast search
        inside of region. Thus each supplied alias point must point to
        a valid application unit. Alias points is used only by app.
    '''

    __slots__ = ('_Alias__rg', '_Alias__alias', )

    ALIAS_ANY   = 0;    ALIAS_BEFORE    = 1;    ALIAS_AFTER     = 2

    def __init__(s, alias = None, rg = (None, None),  **kw):
        IExten.__init__(s, **kw)

        s.__rg      = rg
        s.__alias   = sorted(alias or [])

    def __len__(s):     return len(s.__alias)

    def __iter__(s):    return iter(s.__alias)

    def __desc__(s):
        return '%u aliases' % (len(s),)

    def extend(s, rg, force = False):
        if Alias.__check(rg, s.__alias):
            pass

        elif force is True:
            s.__alias = s.__subset(rg)

        else:
            return False

        s.__rg = rg

        return True

    @classmethod
    def __check(cls, rg, alias):
        bound = alias and (alias[0], alias[-1])

        return not bound or Tools.inside(rg, bound)

    def __args__(s, rg):    return ((s.__subset(rg), rg), {})

    def __subset(s, rg):
        case = lambda z, x, y: y if x is None else z(x)
        find = lambda x: bisect_left(s.__alias, x)

        a, b = map(lambda x: case(find, *x), [(rg[0], 0), (rg[1], len(s))])

        return s.__alias[a:b]

    def lookup(s, at, alias = None):
        ''' Found aliased point for given address '''

        if not Tools.inside(s.__rg, Tools.check(at, False)):
            raise MapOutOf(s, at)

        k = bisect_right(s.__alias, at)

        if 0 < k and s.__alias[k-1] == at:
            return s.__alias[k-1]

        if alias == Alias.ALIAS_BEFORE:
            return s.__alias[k-1] if k > 0 else s.__rg[0]

        elif alias == Alias.ALIAS_AFTER:
            return s.__alias[k] if k < len(s.__alias) else None

        else:
            raise ValueError('invalid alias value')

    def push(s, at):
        ''' Add alias point for given region '''

        at = int(at)

        if not Tools.inside(s.__rg, Tools.check(at, False)):
            raise MapOutOf(s, at)

        k = bisect_right(s.__alias, at)

        if k < 1 or s.__alias[k-1] != at:
            s.__alias.insert(k, at)

    def catch(s, hint):
        ''' Found formal a wild region boundary using aliases '''

        if s.__rg != (None, None):
            raise Exception('only the beast may be catched')

        if len(s.__alias) < 1:
            raise Exception('too low alias points to catch')

        right = max(s.__alias[-1], hint or s.__alias[-1])

        return (s.__alias[0], right)
