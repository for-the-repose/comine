#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.maps  import IMaps
from comine.iface.world import EPhys, IOwner
from comine.core.logger import log
from comine.gdb.targets import Targets
from comine.misc.humans import Humans
from comine.maps.exten  import IExten
from comine.maps.ring   import Ring, Span
from comine.maps.tools  import Tools
from comine.arch.proc   import Maps

class Core(IOwner):
    "Core dump components discover"

    def __init__(s, infer):
        s.__infer   = infer
        s.__ring    = Ring()

        s.__read_maps_target()

        if len(s.__ring) > 0:
            infer.register(s, s.__ring, provide = 'blobs')

            log(2, 'located %s in %u blobs of core' %
                    (Humans.bytes(s.__ring.__bytes__()), len(s.__ring)) )

    def __len__(s): return s.__ring.__len__()

    def __read_maps_target(s):
        for back, rg, section, name in Targets.enum():
            if rg[0] < rg[1]:
                if back == IMaps.BACK_CORE:
                    exten = ECore(rg, infer = s.__infer)

                    span = s.__ring.make(rg, exten = exten)

            else:
                log(8, 'zero span at %x %s' % (rg[0], back))


class Memory(IOwner):
    def __init__(s, infer):
        s.__infer   = infer
        s.__ring    = Ring()
        s.__world   = infer.__world__()

        mmaps = s.__world.by_prov('mmaps')

        if len(mmaps) < 1:
            raise Exception('cannot find mmaps ring')

        for span in mmaps[0]:
            exten = EMem(span.__rg__(), s.__infer)

            s.__ring.make(span.__rg__(), exten = exten)

        s.__infer.register(s, s.__ring, provide = 'blobs')


class Mappings(IOwner):
    def __init__(s, infer):
        s.__infer   = infer
        s.__ring    = Ring()    # maps ring
        s.__mode    = None

    def attach(func):
        def _func(s, *kl, **kw):
            if s.__mode is not None:
                raise Exception('maps already discovered')

            try:
                return func(s, *kl, **kw)

            finally:
                if s.__mode is not None:
                    s.__infer.register(s, s.__ring, provide = 'mmaps')

        return _func

    @attach
    def use_file(s, path):
        if path is not None:
            s.__mode = str(path)

            s.__read_maps_procs(Maps.read(path))

    @attach
    def use_pid(s, pid):
        s.__mode = int(pid)

        s.__read_maps_procs(Maps.pid(int(pid)))

    def __read_maps_procs(s, it):
        mask = IMaps.FLAG_ALL

        for place, flags, entity in it:
            exten = EMaps(flags, mask, entity)

            s.__ring.make(place, exten = exten)


class EInfer(EPhys):
    ''' Wrapper for accessing memory through gdb infer API '''

    __slots__ = ('_EInfer__rg', '_EInfer__infer')

    def __init__(s, rg, infer):
        s.__rg      = rg
        s.__infer   = infer

    def __desc__(s):
        return 'EInfer(aliased to %s)' % Tools.str(s.__rg)

    def extend(s, rg, force = False):
        return s.__rg == rg

    def __rg__(s):  return s.__rg

    def search(s, sub):
        at = s.__rg[0] or 0

        while at is not None and at < s.__rg[1]:
            at = s.__infer.search_memory(at, s.__rg[1] - at, sub)

            if at:
                yield at

                at += len(sub)

    def read(s, at, size):
        return s.__infer.readvar(at, size, False)


class EPadd(EPhys):
    ''' Stub padd emulating physical region '''

    __slots__ = ('_EPadd__rg', '_EPadd__read')

    def __init__(s, rg):
        s.__rg      = rg
        s.__read    = 0

    def __rg__(s):      return s.__rg

    def __readed__(s):  return s.__read

    def read(s, at, size):
        s.__read += size

        return '\0' * size


class ECore(EInfer):
    def __desc__(s):    return 'Core'


class EMem(EInfer):
    def __desc__(s):    return 'Mem'


class EMaps(IExten):
    __slots__ = ('_EMaps__flags', '_EMaps__mask', '_EMaps__entity')

    def __init__(s, flags = None, mask = None, entity = None, **kw):
        IExten.__init__(s, **kw)

        s.__flags   = flags
        s.__mask    = mask
        s.__entity  = entity

    def __desc__(s):
        flit = IMaps.flags_to_sym(s.__flags, s.__mask)
        elit = '?' if s.__entity is None else s.__entity

        return 'Maps(%s %s)' % (flit, elit)

    def extend(s, rg, force = False):
        return True
