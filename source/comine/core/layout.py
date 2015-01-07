#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from os         import stat, access, lstat, listdir, mkdir, X_OK
from os.path    import abspath, split, exists, isfile, isdir
from re         import match
from itertools  import ifilter, islice

from comine.iface.infer import ILayout, LayoutError

class Layout(ILayout):
    '''
        Standard files layout handler. Eeach directory should

        1. Contain a one or more core files made with the same binary
            file and named as core.SUFFIX;

        2. Contain binary named 'binary' or has the only file within
            directory with executable bit set;

        3. Pepared root directory with exact tree structure of original
            host having used shared libraries files and optionally its
            .debug conterparts. Directory should be palced with name
            'root';


        Each directory may hold the following optional suff

        4. Copy of /proc/$P{PID}/maps file just before core being dropped
            under name 'maps'. Current host root tree will be used if
            there is no provided optional root.

        5. Saved cache data in subdir '.cache', generated only by comine
            code and its plugins, objects lifetime under this directory is
            entirely controlled by comine.

        6. Reserved subdir '.temp' for temporary files.
    '''

    def __init__(s, path):
        s.__slots = dict(map(lambda x: (x, []), _Meta.keys()))

        s.__base    = None
        s.__bin     = None
        s.__maps    = None
        s.__root    = None
        s.__core    = None

        s.__locate(path)

    def __binary__(s):  return s.__abs(s.__bin)

    def __core__(s):    return s.__abs(s.__core)

    def __maps__(s):    return s.__abs(s.__maps)

    def __root__(s):    return s.__abs(s.__root)

    def special(s, kind, make = True):
        if kind not in ('cache', 'temp'):
            raise ValueError('Unknown special sub %u' % kind)

        path = abspath(s.__base + '/.%s' % kind)

        if isdir(path):
            pass

        elif exists(path):
            raise Exception('special path for %s alrady used' % kind)

        elif make is True:
            mkdir(path)

        else:
            return None

        return path

    def __locate(s, path):    # -> (binary, core, root, maps)
        s.__examine_path(path)

        for name in listdir(s.__base):
            for slot in _Meta().check(s.__base, name):
                if slot in s.__slots:
                    s.__slots[slot].append(name)

        s.__select_core()
        s.__select_binary()

        s.__maps = (s.__slots.get('maps') or [None])[0]
        s.__root = (s.__slots.get('root') or [None])[0]

    def __examine_path(s, path):
        if isfile(path):
            s.__base, s.__core = split(path)

        elif isdir(path):
            s.__base, s.__core = path, None

        else:
            raise LayoutError('path to core file is not exists')

    def __select_core(s):
        cores = s.__slots.get('core', [])

        if s.__core and s.__core in cores:
            pass

        elif s.__core is not None:
            raise LayoutError('Core "%s" was not found in layout' % s.__core)

        elif len(cores) == 0:
            raise LayoutError('Core files was not found in layout')

        elif len(cores) > 1:
            pat = '%u cores found, pass explicitly one'

            raise LayoutError(pat % len(cores))

        else:
            s.__core = cores[0]

    def __select_binary(s):
        bins = s.__slots.get('binary')

        if len(bins) < 1:
            raise LayoutError('Binary file was not found in layout')

        elif len(bins) == 1:
            s.__bin = bins[0]

        elif 'binary' in bins:
            s.__bin = 'binary'

        else:
            raise LayoutError('Too many binaries exists in layout')

    def __abs(s, sub):
        return abspath(s.__base + '/' + sub) if sub else None


class _Meta(object):
    FILE = 1;   EXEC = 2;   DIR = 3

    __SLOTS = (
        ('core',    False,  FILE,   ('core(\.[\w\d]+)?',) ),
        ('root',    False,  DIR,    ('root',) ),
        ('maps',    False,  FILE,   ('maps',) ),
        ('binary',  False,  EXEC,   ('binary',) ),
        ('.cache',  False,  DIR,    ('.cache',) ),
        ('.temp',   False,  DIR,    ('.temp',) ),
        ('binary',  True,   EXEC,   ('.+',) ),
    )

    def check(s, base, name):
        found, full = False, base + '/' + name

        if exists(full):
            for slot, weak, kind, pats in _Meta.__SLOTS:
                if weak and found:
                    pass    # Ignore low priotity patterns

                elif _Meta.__match(pats, name):
                    found = True

                    if kind == _Meta.FILE:
                        res = isfile(full) and not access(full, X_OK)

                    elif kind == _Meta.EXEC:
                        res = isfile(full) and access(full, X_OK)

                    elif kind == _Meta.DIR:
                        res = isdir(full)

                    else:
                        continue

                    if res is True:
                        yield slot

                    elif not weak:
                        raise LayoutError('Invalid slot "%s" content' % slot)

    @classmethod
    def keys(cls):
        it = map(lambda x: x[0], cls.__SLOTS)

        return filter(lambda x: not x.startswith('.'), it)

    @classmethod
    def __match(cls, pats, name):
        it = ifilter(lambda x: match(x, name), pats)

        return sum(1 for _ in islice(it, 1)) > 0
