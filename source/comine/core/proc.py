
from re     import match, VERBOSE

class Maps(object):
    FL_READ     = 0x01
    FL_WRITE    = 0x02
    FL_EXEC     = 0x04
    FL_SHARED   = 0x08

    __PL = '''
            \s*([\w]+)\s*-\s*([\w]+)
            \s+([rwxps-]{4})
            \s+(\w+)
            \s+(\d+):(\d+)
            \s+(\d+)
            \s+(.*)
    '''

    __FSYM = { 'r' : FL_READ, 'w' : FL_WRITE, 'x' : FL_EXEC,
                's' : FL_SHARED, 'p' : 0,  '-' : 0 }

    @classmethod
    def parse(cls, line): # -> (rg, perm, offset, inode, desc)
        g = match(cls.__PL, line, VERBOSE)

        if g is not None:
            g = g.groups()

            inode = tuple(map(int, g[4:7]))

            flags = reduce(lambda x, y: x | y,
                            map(lambda z: cls.__FSYM[z], g[2]))

            desc = g[7].strip()

            return (int(g[0], 16), int(g[1], 16), flags, int(g[3], 16), desc)
