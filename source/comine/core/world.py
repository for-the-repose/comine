#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from re     import match

from comine.iface.world import IOwner, EPhys
from comine.misc.types  import Types
from comine.misc.segen  import Segen
from comine.misc.puts   import Puts
from comine.misc.func   import gmap
from comine.maps.span   import Span
from comine.maps.ring   import Ring
from comine.maps.walk   import Walk, Diff, Glide, Delay
from comine.core.base   import EMaps, EMem, ECore, EPadd
from comine.core.freg   import Freg

class World(object):
    USAGE_UNKNOWN   = 0;    USAGE_CONFLICT  = 1
    USAGE_UNUSED    = 2;    USAGE_VIRTUAL   = 3

    def __init__(s, model):
        s.__seq     = Segen()
        s.__model   = model
        s.__rings   = {}    # class -> [ Rec() ]
        s.__by_seq  = {}    # seq   -> Rec()
        s.__by_prov = {}

    def __iter__(s):
        for items in s.__rings.values():
            for rec in items: yield rec

    def __model__(s):   return s.__model

    def lookup(s, at, pred = None): # -> [ (offset, rec, span) ]
        def _get(rec):
            span = rec.__ring__().lookup(at)[1]

            if span is not None and (not pred or pred(span)):
                offset = at - span.__rg__()[0]

                return (offset, rec, span)

        return filter(None, map(_get, s))

    def search(s, blob):    # -> [ (at, offset, span) ]
        walk = Walk(map(lambda x: x.__ring__(), s))

        for span in walk.order(pred = Pred.phys):
            for at in span.exten().search(blob):
                offset = at - span.__rg__()[0]

                yield (at, offset, span)

    def validate(s, at):    # -> (reliability, result)
        at = int(at)

        # get actual maps. If maps exists, use it
        # if not, use core and exuns

    def physical(s, place, unused = None, bins = False):
        '''
            Enums physical memory as (place, [ spans ]) with:

                1. Unused by rings supplied in unused arg

                2. Include executable units if bins is set to True
        '''

        pred, walk = Pred.phys, s.__walk_phys(bins = bins)

        if unused is None:
            for rg, spans in walk.group(place, pred, empty = False):
                yield rg, spans

        else:
            two = unused if isinstance(unused, tuple) else [ unused ]

            diff = Diff(one = (walk, pred), two = two)

            for rg, spans, _ in diff(place, what = Diff.YIELD_ONE):
                yield rg, spans

    def enum(s, unused = False, conflict = False, virtual = False):
        walk = Walk(map(lambda x: x.__ring__(), s))

        for rg, spans in walk.change(None, empty = False):
            phys  = filter(Pred.phys, spans)
            logic = filter(Pred.logic, spans)

            if len(logic) > 1:
                if conflict is True:
                    yield (World.USAGE_CONFLICT, rg, phys, logic)

            elif len(logic) < 1 and phys:
                if unused is True:
                    yield (World.USAGE_UNUSED, rg, phys, None)

            elif len(logic) >  0 and not phys:
                if virtual is True:
                    yield (World.USAGE_VIRTUAL, rg, None,  logic)

    def addrs(s, maps = False, gran = 0):
        ''' Return address space predicate object '''

        names = ['blobs', 'exun', 'mmap' if maps else None]

        walk = Walk(rings = list(s.__get_rings(names)))

        it = gmap(lambda x: x[0], walk.group(None, None, empty = False))

        return Freg(list(it), model = s.__model, gran = gran)

    def by_iface(s, iface):
        return s.__rings.get(iface)

    def by_seq(s, seq):
        return s.__by_seq.get(seq)

    def by_prov(s, provide):
        it = s.__by_prov.get(provide, [])

        return map(lambda x: x.__ring__(), it)

    def by_path(s, line):
        '''
            Path to piece of memory selector:
                path := ( role | seq ) [ '.' [ span_seq ] ]
        '''

        g = match('([\w\d]+)(?:\.(\d+))?', line)

        if g is None:
            raise Exception('cannot parse path=%s' % line)

        rlit, seq = g.groups()

        try:
            rings = s.__by_seq.get(int(rlit))

        except ValueError:
            rings = s.__by_prov.get(rlit)

        if len(rings or []) > 1:
            raise Exception('too many rings found with %s' % path)

        elif rings is None:
            return None

        elif seq is None:
            return rings[0].__ring__()

        else:
            return rings[0].__ring__().by_seq(int(seq))

    def save(s, entity, base, padd = False):
        '''
            Dump content of target, place or span, to

                1. one file with unknown regions padded with zeroes
                    if padd argument is set to True;

                2. set of files with content of all known contigous
                    regions in a given range span;

            Returns tuple (chunks, written, padded)
        '''

        series = s.__series_from_entity(entity)

        with Puts(base, label = True) as puts:
            back    = EPadd(rg = (None, None))
            glide   = Glide(s.__walk_phys())

            for place in series:
                it = glide(place, Pred.score, pred = Pred.phys)

                s.__dump_iter(puts, it, padd and back)

            return puts.__stats__() + (back.__readed__(),)

    def __series_from_entity(s, entity):
        if isinstance(entity, Span):
            return [ entity.__rg__() ]

        elif isinstance(entity, Ring):
            return entity.enum(conv = lambda x: x.__rg__())

        elif isinstance(entity, tuple):
            return [ Tools.check(entity, extend = False) ]

        else:
            raise TypeError('cannot get region from %s' % entity)

    def __dump_iter(s, puts, it, back):
        puts.close()

        for rg, span in it:
            if not span and not back:
                puts.close()

            else:
                if not puts.__ready__():
                    puts.next('_%016x.chunk' % rg[0])

                exten = span and span.exten()

                (exten or back).dump(puts, rg)

    def push(s, owner, ring, provide = None, use = None, uniq = True):
        if not isinstance(owner, IOwner):
            raise Exception('Invalid ring owner instance=%s' % str(owner))

        World.__check_prov_name(provide)

        rec = Rec(owner, ring, provide, use, seq = s.__seq())

        World.__add(s.__rings, owner.__class__, rec, uniq)

        s.__by_seq[rec.__seq__()] = rec

        uprov = World.__is_uniq_prov(provide)

        World.__add(s.__by_prov, provide, rec, uniq = uprov)

    def __walk_phys(s, bins = True):
        names = ['blobs']

        if bins is True:
            names.append('exun')

        return Walk(rings = list(s.__get_rings(names)))

    def __get_rings(s, names):
        it = s.__get_names(names)

        return gmap(lambda x: x[0].__ring__(), it)

    def __get_names(s, names):
        return filter(None, map(lambda x: s.__by_prov.get(x), names))

    @classmethod
    def __check_prov_name(cls, name, throw = True):
        if name is not None:
            try:
                int(name)

            except ValueError:
                return True

            else:
                if throw is False:
                    return False

                raise Exception('invalid provider name=%s' % name)

    @classmethod
    def __is_uniq_prov(cls, provide):
        return provide in ('blobs', 'exun', 'mmaps')

    @classmethod
    def __add(cls, di, key, val, uniq = True):
        if key is not None:
            it = di.get(key, [])

            if uniq is True and len(it) > 0:
                raise Exception('already set')

            elif len(filter(lambda x: x == val, it)) > 0:
                raise Exception('already set')

            it.append(val)

            if len(it) == 1:
                di[key] = it


class Rec(object):
    __slots__ = ('_Rec__owner', '_Rec__name', '_Rec__ring',
                    '_Rec__provide', '_Rec__use', '_Rec__seq')

    def __init__(s, owner, ring, provide = None, use = None, seq = None):
        Types.reset(s)

        s.__owner   = owner
        s.__ring    = ring
        s.__provide = provide
        s.__use     = use
        s.__seq     = seq

    def __str__(s):
        return 'Rec(%u, %s, %s)' \
                    % (s.__seq,
                        s.__provide,
                        str(s.__owner))

    def cmp(s, other):  return other is s.__owner

    def __seq__(s):     return s.__seq

    def __key__(s):     return (s.__owner, s.__name)

    def __iter__(s):    return iter(s.__ring)

    def __prov__(s):    return s.__provide

    def __use__(s):     return s.__use

    def __ring__(s):    return s.__ring

    def __owner__(s):   return s.__owner


class Pred(object):
    @staticmethod
    def phys(span):
        return isinstance(span.exten(), EPhys)

    @staticmethod
    def logic(span):
        return not isinstance(span.exten(), (ECore, EMaps))

    @staticmethod
    def score(span):
        return 1 if isinstance(span.exten(), (ECore, EMem)) else 2
