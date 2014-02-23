#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from re     import match, VERBOSE

from comine.iface.maps  import *

class Maps(object):
    __PL = '''
            \s*([\w]+)\s*-\s*([\w]+)
            \s+([rwxps-]{4})
            \s+(\w+)
            \s+(\d+):(\d+)
            \s+(\d+)
            \s+(.*)
    '''

    __FSYM = { 'r' : IMaps.FLAG_READ, 'w' : IMaps.FLAG_WRITE,
                'x' : IMaps.FLAG_EXEC, 's' : IMaps.FLAG_SHARED,
                'p' : 0,  '-' : 0 }

    @classmethod
    def pid(cls, pid):
        if not isinstance(pid, int):
            raise TypeError('invalid pid type=%s' % pid)

        for rg in cls.read('/proc/%u/maps' % pid): yield rg

    @classmethod
    def read(cls, path, require = False):
        with open(path, 'r') as F:
            for rg in map(cls.parse, F):
                if rg is not None:
                    yield rg

                elif require is True:
                    raise ValueError('maps file is damaged')

    @classmethod
    def parse(cls, line): # -> (rg, perm, offset, inode, desc)
        g = match(cls.__PL, line, VERBOSE)

        if g is not None:
            g = g.groups()

            flags = reduce(lambda x, y: x | y,
                            map(lambda z: cls.__FSYM[z], g[2]))

            entity = cls.__entity(g[4:7], g[3], g[7].strip())

            return ((int(g[0], 16), int(g[1], 16)), flags, entity)

    @classmethod
    def __entity(cls, inode, offset, desc):
        if len(desc) < 1:
            return Anonymous()

        elif desc[0] == '/':
            inode = tuple(map(int, inode))

            return Mapped(inode, int(offset,16), desc)

        elif len(desc) > 2:
            g = match('^\[(?:(stack)(?::(\d+))?|(.*))\]$', desc)

            if g is not None:
                if g.group(1) is not None:
                    return Stack(ppid = g.group(2) and int(g.group(2)))

                else:
                    return Special(kind = g.group(3))
