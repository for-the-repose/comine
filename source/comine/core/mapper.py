#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from sys    import stdout
from re     import match
from bisect import bisect_right

import gdb

from comine.core.exun   import DSO, Binary
from comine.core.libc   import addr_t
from comine.core.proc   import Maps

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

    TARGET_NONE     = 0
    TARGET_CORE     = 1
    TARGET_EXEC     = 2

    REL_UNKNOWN     = 0
    REL_OWNER       = 1
    REL_PRETEND     = 2
    REL_USER        = 3

    USAGE_RAW       = 0
    USAGE_ALLOC     = 1
    USAGE_STACK     = 2
    USAGE_UNUSED    = 3
    USAGE_EXEC      = 4

    def __init__(s):
        s.__secs        = []
        s.__maps        = []
        s.__regs        = []
        s.__flats       = []
        s.__bin         = None
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

    def register(s, rg, relation, category, target):
        # TODO: walk through ranges and check intersecions

        s.__regs.append((rg, relation, category, target))

    def flats(s, at):
        for rg in s.__flats:
            if rg[0] <= at < rg[1]: return rg

    def lookup(s, at, usage = None):
        if not s.validate(at): return None

        rec = s.__lookup_fast(at)

        if rec and (usage is None or rec[2] in usage):
            return rec

    def enum(s, larger = None):
        for rg, a, b, target in s.__regs:
            if larger and rg[1] - rg[0] < larger:
                continue

            yield rg, a, b, target

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
        state = Mapper.TARGET_NONE

        lines = gdb.execute('info target', to_string = True)

        for line in lines.split('\n'):
            line = line.strip()

            g = match('(0x[\da-f]+) - (0x[\da-f]+) is (.*)', line)

            if g is not None:
                g = g.groups()

                rg = ((int(g[0], 16), int(g[1], 16)))

                m = match('(\.[\w._-]+)(?:\s+in\s+(.*))?', g[2])

                if m is not None:
                    section = m.group(1).strip()
                    name = (m.group(2) or '').strip()

                    if not name:
                        if s.__bin is None: s.__bin = Binary()

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

                    if section == '.text':
                        usage = Mapper.USAGE_EXEC
                    else:
                        usage = Mapper.USAGE_RAW

                    s.register(rg, Mapper.REL_OWNER, usage, target)

                elif state == Mapper.TARGET_CORE:
                    s.register(rg, Mapper.REL_UNKNOWN, Mapper.USAGE_RAW, None)
                    s.__flats.append(tuple(rg))

            else:
                g = match('Local ([\w\s]+) file:', line)

                if g and g.group(1) == 'core dump':
                    state = Mapper.TARGET_CORE
                elif g and g.group(1) == 'exec':
                    state = Mapper.TARGET_EXEC

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


