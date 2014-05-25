#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.misc.types  import Types

class Segen(object):
    __slots__ = ('_Segen__seq', '_Segen__reuse')

    def __init__(s, start = 0, reuse = True):
        s.__seq     = start
        s.__reuse   = [] if reuse else None

    def __call__(s):
        if s.__reuse:
            return s.__reuse.pop()

        else:
            try:
                return s.__seq

            finally:
                s.__seq += 1

    def reuse(s, seq):
        if None not in (s.__reuse, seq):
            s.__reuse.append(int(seq))

    def drop(s):
        s.__reuse = []


class ScnOutOfSync(Exception):
    pass


class Scn(object):
    __slots__ = ('_Scn__seq', )
    def __init__(s):
        s.__seq     = 0

    def __seq__(s):     return s.__seq

    def __int__(s):     return s.__seq

    def __str__(s):     return 'Scn(%08x)' % s.__seq

    def alter(s):       s.__seq += 1


class ScnRef(object):
    __slots__ = ('_ScnRef__ref', '_ScnRef__scn')

    def  __init__(s, ref, _type = None):
        s.__ref = Types.ensure(ref, _type)

        s.sync()

    def __call__(s):    return s.__ref

    def __desc__(s):
        slit = 'f' if s.valid() else 's'

        return '%s:%x08u' % (slit, s.__ref.__scn__())

    def valid(s, sync = False):
        try:
            return s.__scn == s.__ref.__scn__()

        finally:
            if sync: s.sync()

    def sync(s):
        s.__scn = s.__ref.__scn__()

    def check(s):
        if not s.valid():
            raise ScnOutOfSync()
