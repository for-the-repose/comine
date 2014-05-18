#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from os         import stat, access, lstat, listdir, X_OK
from os.path    import abspath, split, exists, isfile, isdir
from re         import match
from itertools  import takewhile

from comine.iface.infer import ILayout

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

        4. Optionally copy of /proc/$P{PID}/maps file just before core
            being dropped under name 'maps'. Current host root tree will
            be used if there is no provided optional root.
    '''

    def __init__(s, path):
        s.__slots = dict(map(lambda x: (x, []), _Meta.SLOTS.keys()))

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

    def __locate(s, path):    # -> (binary, core, root, maps)
        if not isfile(path):
            raise Exception('path to core file is not exists')

        s.__base, s.__core = split(path)

        for name in listdir(s.__base):
            for slot in _Meta().check(s.__base, name):
                s.__slots[slot].append(name)

        if s.__core not in s.__slots.get('core', []):
            raise Exception('Core file "%s" was not found in layout' % s.__core)

        s.__select_binary()

        s.__maps = (s.__slots.get('maps') or [None])[0]
        s.__root = (s.__slots.get('root') or [None])[0]

    def __select_binary(s):
        bins = s.__slots.get('binary')

        if len(bins) < 1:
            raise Exception('Binary file was not found in layout')

        elif len(bins) == 1:
            s.__bin = bins[0]

        elif 'binary' in bins:
            s.__bin = 'binary'

        else:
            raise Exception('Too many binaries exists in layout')

    def __abs(s, sub):
        return abspath(s.__base + '/' + sub) if sub else None


class _Meta(object):
    FILE = 1;   EXEC = 2;   DIR = 3

    SLOTS = {
        'core':     ( FILE,  ('core(\.[\w\d]+)?',) ),
        'binary':   ( EXEC,  ('binary', '.+') ),
        'maps':     ( FILE,  ('maps',) ),
        'root':     ( DIR,   ('root',) ),
    }

    def check(s, base, name):
        full = base + '/' + name

        if exists(full):
            for slot, (kind, pats) in _Meta.SLOTS.iteritems():
                if _Meta.__match(pats, name):
                    if kind == _Meta.FILE:
                        res = isfile(full) and not access(full, X_OK)

                    elif kind == _Meta.EXEC:
                        res = isfile(full) and access(full, X_OK)

                    elif kind == _Meta.DIR:
                        res = isdir(full)

                    else:
                        continue

                    if res is True: yield slot

    @classmethod
    def __match(cls, pats, name):
        return not list(takewhile(lambda x: not match(x, name), pats))
