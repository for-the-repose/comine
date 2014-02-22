#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from sys    import stdout
from re     import match
from bisect import bisect_right

import gdb

from comine.iface.maps  import IMaps
from comine.core.exun   import DSO, Binary
from comine.core.libc   import addr_t
from comine.core.proc   import Maps
from comine.gdb.targets import Targets

def log(lev, string):
    if lev < 8: stdout.write(string + '\n')


class Singleton(type):
    def __init__(cls, name, kl, kw):
        super(Singleton, cls).__init__(name, kl, kw)

        cls._instance = None

    def __call__(cls, *kl, **kw):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*kl, **kw)

        return cls._instance


class Mapper(object):
    ''' Memory region mappings table registery '''

    __metaclass__ = Singleton

    def __init__(s):
        s.__secs        = []
        s.__maps        = []
        s.__regs        = []
        s.__flats       = []
        s.__bin         = Binary()
        s.__dso         = {}

        s.__infer   = gdb.selected_inferior()

        s.__read_maps_target()
#        s.__read_maps_sects()

        log(1, 'Mapper ready, has %i regions and %i dso'
                    % (len(s.__regs), len(s.__dso)) )

        class _Rg(object):
            __slots__ = ('point', 'ref')

            def __init__(s, addr, ref):
                s.point = addr
                s.ref   = ref

            def __int__(s):     return s.point

            def __cmp__(s, b):  return cmp(s.point, int(b))

        s.__idx_0 = sorted(map(lambda x: _Rg(x[0][0], x), s.__regs))

    def validate(s, pointer, ro = False):
        addr = int(pointer)

        #__ amd64 ABI allows only 48 bit pointers
        if pointer >> 48: return False

        #__ lookup in the mappings table

        return True

    def register(s, rg, target):
        # TODO: walk through ranges and check intersecions

        s.__regs.append((rg, target))

    def flats(s, at):
        for rg in s.__flats:
            if rg[0] <= at < rg[1]: return rg

    def lookup(s, at, usage = None):
        if not s.validate(at): return None

        rec = s.__lookup_fast(at)

        if rec and (usage is None or rec[2] in usage):
            return rec

    def enum(s, larger = None):
        for rg, target in s.__regs:
            if larger and rg[1] - rg[0] < larger:
                continue

            yield rg, None, None, target

    def search(s, sub):
        for rg, _, _, _ in s.enum():
            at = rg[0]

            while at and at < rg[1]:
                at = s.__infer.search_memory(at, rg[1] - at, sub)

                if at:
                    yield (rg, at)

                    at += len(sub)

    def __lookup_slow(s, at):
        for rec in s.__regs:
            rg = rec[0]

            if rg[0] <= at < rg[1]: return rec

    def __lookup_fast(s, at):
        x1 = bisect_right(s.__idx_0, at) - 1

        if x1 > -1:
            rec = s.__idx_0[x1].ref

            if (rec[0][0] <= at < rec[0][1]):
                return rec

    def __read_maps_target(s):
        for prov, rg, section, name in Targets.enum():
            if prov == IMaps.PROV_CORE:
                s.register(rg, None)
                s.__flats.append(tuple(rg))

            elif prov == IMaps.PROV_EXUN:
                if not name:
                    s.__bin.push(name, rg)

                    target = s.__bin

                else:
                    if name is not None:
                        dso = s.__dso.get(name)

                        if dso is None:
                            dso = DSO(name)

                            s.__dso[name] = dso

                    target = dso

                target.push(section, rg)

                s.register(rg, target)

    def __read_maps_sects(s):
        infer = gdb.selected_inferior()

        with open('/proc/%u/maps' % infer.pid, 'r') as F:
            for rg in map(Maps.parse, F):
                pass

    @classmethod
    def readvar(cls, var, size, gdbval = True, constructor = None):
        ''' Read blob from given memory location '''

        if gdbval is True:
            return var

        else:
            inf = gdb.selected_inferior()

            if isinstance(var, gdb.Value):
                var = int(var.cast(addr_t))

            blob = inf.read_memory(var, size)

            return (constructor or (lambda x: x))(blob)

    @classmethod
    def varptr(cls, var, type_t = None):
        if type_t is None:
            type_t = var.type.pointer()

        return gdb.Value(var.address).cast(type_t)

