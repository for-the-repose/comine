#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.misc.humans import Humans
from comine.misc.types  import Types
from comine.maps.exten  import IExten
from comine.maps.tools  import Tools
from comine.maps.errors import MapError, MapOutOf

class Span(object):
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

    '''

    __slots__ = ('_Span__rg', '_Span__tags', '_Span__ref', '_Span__exten')

    TAG_EXACT   = 0;    TAG_LEAST   = 1;    TAG_MOST    = 2

    TAGS_DEFAULT = (TAG_EXACT, TAG_EXACT)

    I_AM_THE_BEAST  = 1;    I_AM_A_WILD     = 2

    KEEP_BEFORE = 0x1;  KEEP_AFTER  = 0x2;  KEEP_SELF   = 0x4

    KEEP_DROP   = KEEP_BEFORE | KEEP_AFTER
    KEEP_ALL    = KEEP_DROP | KEEP_SELF

    def __init__(s, rg = (None, None), tags = None, exten = None):
        s.__rg      = Tools.check(rg)
        s.__ref     = None
        s.__tags    = tags or Span.TAGS_DEFAULT
        s.__exten   = Types.ensure(exten, IExten, True)

        if s.__exten is not None and not s.__exten.extend(s.__rg):
            raise Exception('cannot attach exten to span')

    def __len__(s):     return Tools.len(s.__rg)

    def __cmp__(s, b):  return cmp(s.__rg[0], b)

    def __contains__(s, at):
        return s.is_inside(at)

    def __repr__(s):
        plit = '*' if s.__ref is None  else ('#%u' % s.__ref[1])

        return 'Span(%s %s%s)' % (plit, Tools.str(s.__rg), s.desc())

    def desc(s, prep = ' '):
        return '' if s.__exten is None else (prep +  s.__exten.__desc__())

    def __rg__(s):      return s.__rg

    def __ref__(s):     return s.__ref

    def __ring__(s):    return s.__ref and s.__ref[0]

    def __seq__(s):     return s.__ref and s.__ref[1]

    def __bind(s, ring, seq = None):
        "Binds region to Ring() object"

        if ring is None:
            s.__ref = None

        elif s.__ref is not None and s.__ref[0] != ring:
            raise Exception('already binded to ring %s' % s.__Ref)

        else:
            s.__ref = (ring, seq)

    def __alter(s, rg):
        if s.__ref is None or s.__ref[0]._Ring__update(s, rg):
            s.__rg = rg

    def human(s):
        ''' Return string with human readable region size '''

        return 'wild' if None in s.__rg else Humans.bytes(len(s))

    def ami(s, what):
        ''' Ask me who I am '''

        if what == Span.I_AM_THE_BEAST:
            return (None, None) == s.__rg
        elif what == Span.I_AM_A_WILD:
            return None in s.__rg
        else:
            raise ValueError('invalid attribute')

    def check(s, icl):  return isinstance(s.__exten, icl)

    def exten(s, make = None):
        if make is not None:
            if s.__exten is None:
                s.__exten = make()

            elif not isinstance(s.__exten, make):
                raise TypeError('Invalid exten=%s' % s.__exten)

        return s.__exten

    def is_inside(s, rg):
        return Tools.inside(s.__rg, Tools.check(rg, True))

    def is_isects(s, rg):
        return Tools.isect(s.__rg, Tools.check(rg, False))

    def cut(s, at, keep):
        if keep not in (Span.KEEP_BEFORE, Span.KEEP_AFTER):
            raise ValueError('Invalid relation=%s' % keep)

        _, rg = s.__split_sub((at, at), keep, empty = True)

        return (s.narrow(rg, give = True) or [None])[0]

    def extend(s, rg = None, where = None, to = None, tag = None):
        if rg and (None, None) == (where, to):
            s.__extend(rg)

        elif rg is None and None not in (where, to):
            if where < 0 and to < s.__rg[0]:
                s.__extend(rg = (to, s.__rg[1]))

            elif where > 0 and to > s.__rg[1]:
                s.__extend(rg = (s.__rg[0], to))
        else:
            raise Exception('Invalid args passed')

    def narrow(s, rg, give = False):
        it = list(s.__narrow(rg, give))

        return it if give is True else None

    def split(s, rg, flags = 0):
        '''
            Split region to three parts by given region. Func yields
            at most 3 new spans depending on rg intersection with self,
            flags arg settings:

            KEEP_ flags tells which splitted spans will be in result.

            EXTEND_ flags set mode extension.
        '''

        return list(s.__split(rg, flags & Span.KEEP_ALL))

    def replace(s, rg, flags = 0):
        '''
            Same as split() func but replace self span in attached Ring()
            object with produces results.
        '''

        it = list(s.__split(rg, flags & Span.KEEP_ALL))

        if s.__ref is not None:
            ref = s.__ref[0].pop(s)

            for mine, span in it: ref.push(span)

        return it

    def __narrow(s, rg, give = False):
        if give is True:
            for mine, span in s.__split(rg, Span.KEEP_DROP):
                if mine is False: yield span

        if s.is_isects(rg):
            s.__extend(rg, force = True, check = False)

        else:
            s.__alter(None)

    def __split(s, rg, flags = 0, bound = 0):
        rg = Tools.extend(s.__rg, Tools.check(rg, False), bound)

        if s.__extend_check(rg) is False:
            raise MapError('cannot extend span %s to %s' % (s, Tools.str(rg)))

        for mine, _rg in s.__split_it(rg, flags):
            yield (mine, s.__subset(_rg))

    def __extend(s, rg, force = False, check = True):
        rg = s.__split_check(rg)

        if check and s.__extend_check(rg) is False:
            raise MapError('cannot extend span %s to %s' % (s, Tools.str(rg)))

        if s.__exten and not s.__exten.extend(rg, force):
            raise MapError('cannot extend due to exten conflicts')

        s.__alter(rg)

        return s

    def __split_check(s, rg, extend = None):
        rg = Tools.check(rg, extend)

        if not s.is_isects(rg):
            raise MapOutOf(s, rg)

        return rg

    def __split_exten(s, rg, extend):
        if s.__exten is None:
            return None

        elif extend and not s.__exten.extend(rg):
            raise Exception('Cannot extend extension')

        elif extend:
            return s.__exten

        else:
            return s.__exten.subset(rg)

    def __split_it(s, by, flags):
        order = (Span.KEEP_AFTER, Span.KEEP_SELF, Span.KEEP_BEFORE)

        for flag, rg in map(lambda x: s.__split_sub(by, x), order):
            if Tools.empty(rg) is False and (flag & flags):
                yield (bool(flag & Span.KEEP_SELF), rg)

    def __split_sub(s, rg, flag, empty = False):
        filt = lambda a, b: None if (a == b and not empty) else (a, b)

        if flag == Span.KEEP_BEFORE:
            return flag, filt(s.__rg[0], rg[0])

        elif flag == Span.KEEP_SELF:
            return flag, rg

        elif flag == Span.KEEP_AFTER:
            return flag, filt(rg[1], s.__rg[1])

        else:
            raise ValueError('unknown flag=%s' % flag)

    def __subset(s, rg):
        exten = s.__split_exten(rg, False)

        return Span(rg, exten = exten)

    def __extend_check(s, place):
        if s.is_inside(place):
            return True

        elif s.__ref:
            wide = s.__ref[0].wider(place)

            return wide and Tools.inside(wide, place)
