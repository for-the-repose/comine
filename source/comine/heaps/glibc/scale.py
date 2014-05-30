#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.misc.types  import Frozen
from .errors			import ErrorChunk
from .defs              import Flags

class Scale(Frozen):
    def __init__(s, libc, page):
        s.__page    = page

        s.type_t = gdb.lookup_type('struct malloc_chunk').pointer()

        s.ptr_t     = libc.std_type('ptr_t')
        s.__addr_t  = libc.std_type('addr_t')
        s.__size_t  = libc.std_type('size_t')

        s.__atom    = int(s.__size_t.sizeof)

        assert s.__page > 4 * s.__atom

        s.__MIN     = s.__atom * 4
        s.__FENCE   = s.__atom * 2
        s.OFFSET    = s.__atom * 2
        s.__ALIGN   = s.__atom * 2
        s.__BRUTT   = s.__atom * 1
        s.__MINETT  = s.__MIN - s.__BRUTT

        s.__mask    = s.__ALIGN - 1

        if s.__mask & (s.__mask + 1):
            raise Exception('invalid align mask=0x%x' % mask)

        Frozen.__init__(s)

    def __page__(s):    return s.__page

    def __atom__(s):    return s.__atom

    def __str__(s):
        return 'Metrics(%u, page=%u)' % (s.__atom, s.__page)

    def at(s, chunk, off = False):
        ''' Convert chunk pointer to pythonic long object '''

        return long(chunk.cast(s.__addr_t)) + (s.OFFSET if off else 0)

    def begin(s, at):
        ''' Return chunk pointer by its first allocated byte '''

        return (at.cast(s.ptr_t) - s.OFFSET).cast(s.type_t)

    def inset(s, chunk):
        ''' Return pointer to first chunk interior byte '''

        return chunk.cast(s.ptr_t) + s.OFFSET

    def next(s, chunk):
        ''' Return pointer to next chunk following supplied '''

        return chunk.cast(s.ptr_t) + s.csize(chunk)

    def csize(s, chunk):
        ''' Get brutto chunk size from passed chunk object '''

        a = long(chunk['size'].cast(s.__size_t))

        return a ^ (a & 0x07)

    def fence(s, chunk, last = False):
        size = long(chunk['size'].cast(s.__size_t))

        return (long(size ^ (size & 0x07)) == s.__FENCE
                    and (not last or size & Flags.PREV_IN_USE))

    def fits(s, chunk, fence = False):
        ''' Returns True if chunk size fits to minimal len '''

        size = s.csize(chunk)

        if size < 0:
            raise ErrorChunk(s, 'stupid gdb cannot convert size_t')

        return size >= (s.__FENCE if fence else s.__MIN)

    def netto(s, chunk):    # -> (size, granularity)
        size = s.csize(chunk) - s.__BRUTT

        return (size, s.__ALIGN if size > s.__MINETT else s.__MINETT)

    def info(s, chunk):     # -> (first, size, granulariy)
        return (s.at(chunk, off = True),) + s.netto(chunk)

    def round(s, size, brutto = False):
        ''' Round size to chunk size as it would allocated by heap '''

        size = s.align(max(size + s.__BRUTT, s.__MIN))

        return size if brutto is True else (size - s.__BRUTT)

    def align(s, size):
        ''' Align size to chunk grid, round up to 2 * size_t '''

        size = int(size)

        return (size + s.__mask) ^ ((size + s.__mask) & s.__mask)
