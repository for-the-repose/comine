#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)


from comine.misc.types  import Singleton


class IMaps(object):
    #__ memory span backends
    BACK_CORE   = 1;    BACK_EXUN   = 2;    BACK_MAPS   = 3

    #__ memory span flags
    FLAG_READ   = 0x01;     FLAG_WRITE  = 0x02
    FLAG_EXEC   = 0x04;     FLAG_SHARED = 0x08

    FLAG_RW     = FLAG_READ | FLAG_WRITE

    FLAG_ALL    = FLAG_RW | FLAG_EXEC | FLAG_SHARED

    __SYM_FLAGS = [ (FLAG_READ, 'r'), (FLAG_WRITE, 'w'),
                    (FLAG_EXEC, 'x'), (FLAG_SHARED, 's') ]

    __SYM_BACK  = { BACK_CORE : 'core', BACK_EXUN : 'exun',
                        BACK_MAPS : 'maps' }

    @classmethod
    def flags_to_sym(cls, flags, mask = None):
        if flags is None:
            return '....'

        else:
            def _is(bit, sym):
                if not(mask is None or (mask & bit)):
                    return '.'

                else:
                    return sym if bit & flags else '-'

            return ''.join(map(lambda x: _is(*x), cls.__SYM_FLAGS))

    @classmethod
    def back_to_sym(cls, back):
        return 'none' if back is None else cls.__SYM_BACK[back]


class IEntity(object):
    "Base class for all mapped entitites"

    def __literal__(s):
        raise Exception('Not implemented')


class Anonymous(IEntity):
    __slots__       = tuple()
    __metaclass__   = Singleton

    def __literal__(s): return 'anon'

    def __str__(s):     return 'Anon()'

class Mapped(IEntity):
    __slots__ = ('_Mapped__inode', '_Mapped__path', '_Mapped__offset')

    def __init__(s, inode, offset, path):
        s.__inode   = inode
        s.__offset  = offset
        s.__path    = path

    def __inode__(s):   return s.__inode

    def __offsset__(s): return s.__offset

    def __path__(s):    return s.__path

    def __literal__(s): return 'map'

    def __str__(s):
        return 'Mapped(%s:%s %s, +%x  %s)' \
                    % (s.__inode + (s.__offset, s.__path))


class Stack(IEntity):
    __slots__ = ('_Stack__ppid', )

    def  __init__(s, ppid = None):
        s.__ppid    = ppid

    def __literal__(s): return 'stack'

    def __str__(s):
        plit = '' if s.__ppid is None else ', ppid=%u' % s.__ppid

        return 'Stack(%x%s)' % (id(s), plit)


class Special(IEntity):
    __slots__  = ('_Special__kind', )

    def __init__(s, kind):
        s.__kind    = kind

    def __literal__(s): return s.__kind__()

    def __kind__(s):    return s.__kind

    def __str__(s):
        return 'Special(%x, %s)' % (id(s), s.__kind)

