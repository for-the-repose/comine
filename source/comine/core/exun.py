#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from os.path    import basename

from comine.iface.maps  import IMaps
from comine.iface.world import IOwner
from comine.core.logger import log
from comine.core.base   import EInfer
from comine.gdb.targets import Targets
from comine.misc.segen  import Segen
from comine.misc.humans import Humans
from comine.maps.exten  import IExten
from comine.maps.errors import MapConflict
from comine.maps.ring   import Ring, Span

class Exuns(IOwner):
    def __init__(s, infer):
        s.__segen   = Segen(1)
        s.__infer   = infer
        s.__units   = {}    # { name -> Unit() }
        s.__s2u     = {}    # { seq -> Unit() }
        s.__ring    = Ring()

        s.__read_maps()

        log(1, "discovered %s in %u exuns"
                 % (Humans.bytes(s.__ring.__bytes__()), len(s.__units)))

        infer.register(s, s.__ring, provide = 'exun')

    def __read_maps(s):
        for back, rg, section, name in Targets.enum():
            if back == IMaps.BACK_EXUN:
                if section not in ('.tbss', '.tdata'):
                    infer   = s.__infer_for(section)
                    unit    = s.__locate(name, create = True)
                    ref     = (section, unit)

                    if infer is None:
                        exten = ESect(ref)

                    else:
                        exten = EStatic(ref, rg, infer)

                    try:
                        span = s.__ring.make(rg, exten = exten)

                    except MapConflict as E:
                        log(1, 'cannot push %s %s' % (rg, exten))

                    else:
                        if not unit.push(section, span):
                            log(1, 'cannot add %s for %s' % (section, unit))

    def __infer_for(s, section):
        if section in ('.text', '.rodata', '.ctors', '.dtors'):
            return s.__infer

    def __locate(s, name, create = True):
        unit = s.__units.get(name)

        if unit is None and create is True:
            seq = 0 if not name else s.__segen()

            unit = _Unit(name, seq = seq)

            s.__units[unit.__name__()]  = unit
            s.__s2u[unit.__seq__()] = unit

        return unit


class _Unit(object):
    __slots__ = ('_Unit__name', '_Unit__secs', '_Unit__seq')

    def __init__(s, name = None, seq = None):
        s.__name    = name
        s.__seq     = seq
        s.__secs    = {}

    def __seq__(s):     return s.__seq

    def __name__(s):    return s.__name

    def __str__(s):
        short  = basename(s.__name or '')

        return 'Unit(#%u, %s %u sects)' \
                    % (s.__seq, short,len(s.__secs))

    def sections(s):    return s.__secs.itervalues()

    def push(s, section, span):
        if section not in s.__secs:
            s.__secs[section] = span

            return True


class ESect(IExten):
    __slots__ = ('_ESect__ref', )

    def __init__(s, ref, **kw):
        IExten.__init__(s, **kw)

        s.__ref     = ref

    def __desc__(s):
        return 'ESect(%s, %s)' % s.__ref

    def extend(s, rg, force = False):
        return True


class EStatic(EInfer):
    __slots__ = ('_EStatic__ref', )

    def __init__(s, ref, rg, infer):
        EInfer.__init__(s, rg, infer)

        s.__ref     = ref

    def __desc__(s):
        return 'EStatic(%s, %s)' % s.__ref


