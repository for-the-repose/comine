#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.iface.heap 	import IHeap
from comine.misc.types  import Types
from .errors			import ErrorChunk
from .scale				import Scale
from .defs              import Flags

class Chunk(object):
    TYPE_DEFAULT        = 0
    TYPE_REGULAR        = 1
    TYPE_ALLOCATED      = 2
    TYPE_TOP            = 3
    TYPE_BIN            = 4
    TYPE_FAST           = 5
    TYPE_LEFT           = 6

    _TYPE_BINS = (TYPE_BIN, TYPE_FAST)

    __attrs = ('sc', 'type', 'chunk', 'end', 'queue', 'first', 'arena')

    __slots__ = tuple(map(lambda x: '_Chunk__' + x, __attrs))

    def __init__(s, me, raw, kind_of = None, end = None,
                        queue = None, _arena = None):
        if raw == 0x0: raise ValueError('invalid address')

        s.__sc      = Types.ensure(me, Scale)
        s.__type    = kind_of or Chunk.TYPE_REGULAR

        if s.__type == Chunk.TYPE_ALLOCATED:
            raw     = s.__sc.begin(raw)
            kind_of = Chunk.TYPE_REGULAR

            raise Exception('Not ready yet')

        def _cast(v):
            return v if isinstance(v, gdb.Value) else v and gdb.Value(v)

        raw, end = map(_cast, [raw, end])

        s.__chunk   = raw.cast(s.__sc.type_t)
        s.__end     = end and s.__sc.at(end)
        s.__queue   = queue and int(queue)
        s.__first   = False
        s.__arena   = _arena

        if kind_of not in Chunk._TYPE_BINS and queue is not None:
            raise TypeError('queue applicable for bins only')

        s.__validate__()

    def meta(s):
        ''' Return metadata about of this chunk: (body, size, used) '''

        offset = s.__sc.OFFSET

        return (s.__at__() + offset, len(s) - offset, s.is_used())

    def is_used(s):
        caret = s.clone(Chunk.TYPE_REGULAR).__next__()

        return (caret.flag(Flags.PREV_IN_USE) != 0)

    def clone(s, kind_of):
        return Chunk(s.__sc, s.__chunk, kind_of, _arena = s.__arena)

    def flag(s, flag): return s.__chunk['size'] & (flag & 0x7)

    def prev(s): return int(s.__chunk['prev_size'])

    def arena(s):
        if s.__chunk['size'] & Flags.NON_MAIN_ARENA:
            pass

    def relation(s, at):
        ''' Give relation of given address to this chunk '''

        a = int(at - s.__at__())

        if not (0 <= a < len(s)):
            return (IHeap.REL_OUTOF, a)

        elif a < s.__sc.OFFSET:
            return (IHeap.REL_HEAD, a - s.__sc.OFFSET)

        else:
            return (IHeap.REL_CHUNK, a - s.__sc.OFFSET)

    def __repr__(s):
        return '<Chunk at 0x%x, %x %ub ~%u>' \
                    % ((s.__sc.at(s.__chunk),
                            s.flag(0x7)) + s.__netto__())

    def __validate__(s, fence = False):
        if not s.__sc.fits(s.__chunk, fence):
            raise ErrorChunk(s, 'Invalid chunk size %ib' % len(s))

        if s.__type == Chunk.TYPE_REGULAR: s.__validate_regular()
        elif s.__type == Chunk.TYPE_TOP:   s.__validate_top()
        elif s.__type == Chunk.TYPE_BIN:   s.__validate_bin()
        elif s.__type == Chunk.TYPE_FAST:  s.__validate_fast()

    def __validate_regular(s):
        ''' Regular chunks in heap have restrictions to size, above of
            mmap_thresholds chunks are allocated out of heap segemtns
            and must not be presented in any of chains.
        '''

    def __validate_top(s):
        ''' Chunk before the top is always allocated chunk'''

        if not(s.__chunk['size'] & Flags.PREV_IN_USE):
            raise Exception('Invalid top chunk')

    def __validate_bin(s):
        ''' Restrictions applyed to chunks in bins queue:
            1. always surrounded by allocated chunks,
            2. sorted by size on asc except zero bin
        '''

        if s.__queue > 0 or s.__queue is None:
            if not(s.__chunk['size'] & Flags.PREV_IN_USE):
                raise Exception('Invalid bin chunk')

            caret = s.clone(Chunk.TYPE_REGULAR).__next__()

            if caret.flag(Flags.PREV_IN_USE):
                raise Exception('Invalid bin chunk')

            if caret.prev() != s.__sc.csize(s.__chunk):
                raise Exception('Invalid bin cunk')

            try:
                caret.__next__()

            except StopIteration as E:
                if s.__arena is not None:
                    s.__arena._Arena__fence.append(caret.__at__())

            else:
                if not caret.flag(Flags.PREV_IN_USE):
                    raise ErrorChunk(caret, 'Invalid bin chunk')

    def __validate_fast(s):
        ''' Chunks in fastbins always marked as allocated and
            special restrictions to its size are applied
        '''

        if s.__sc.csize(s.__chunk) >= 512:
            raise Exception('Invalid size %i of fastbin chunk' % len(s))

        caret = s.clone(Chunk.TYPE_REGULAR).__next__()

        if not caret.flag(Flags.PREV_IN_USE):
            raise Exception('Invalid fastbin chunk')

    def __blob__(s, gdbval = False):
        ''' Return blob that holds this chunk or char pointer '''

        size = s.__sc.netto(s.__chunk)[0]

        if gdbval is True:
            return (size, s.__sc.inset(s.__chunk))

        else:
            inf = gdb.selected_inferior()

            return inf.read_memory(s.__at__() + s.__sc.OFFSET, size)

    def __at__(s):      return s.__sc.at(s.__chunk)

    def __rg__(s):      return (s.__at__(), s.__at__() + len(s))

    def inset(s):       return s.__at__() + s.__sc.OFFSET

    def __len__(s):     return s.__sc.csize(s.__chunk)

    def __netto__(s):   return s.__sc.netto(s.__chunk)

    def __eq__(s, chunk):
        if isinstance(chunk, Chunk):
            return s.__at__() == chunk.__at__()
        else:
            raise TypeError('can compare only thin chunk')

    def __iter__(s):
        if s.__end is None and s.__type in (Chunk.TYPE_LEFT, Chunk.TYPE_BIN):
            raise Exception('end point must be set for type=%i'% s.__type)

        if s.__type != Chunk.TYPE_LEFT:
            s.__first = True

        return s

    def __next__(s):
        if s.__first is True:
            s.__first = False

            return s

        elif s.__type == Chunk.TYPE_REGULAR:
            _p = s.__sc.next(s.__chunk)
            caret = _p.cast(s.__sc.type_t)

            if s.__end and s.__sc.at(_p) >= s.__end:
                s.__chunk = caret

                raise StopIteration('terminal chunk is reached')

            if s.__sc.fence(s.__chunk) and s.__sc.fence(caret, True):
                raise StopIteration('fencepoint reached')

        elif s.__type == Chunk.TYPE_BIN:
            caret = s.__chunk['fd']

            if s.__sc.at(caret) == s.__end:
                raise StopIteration()

            if caret['bk'] != s.__chunk:
                raise Exception('Invalid bin chunk linkage')

#           if s.__queue and caret['size'] < s.__sc.csize(s.__chunk):
#               raise Exception('bin is not sorted by size')

        elif s.__type == Chunk.TYPE_FAST:
            caret = s.__chunk['fd']

            if caret == 0x0:
                raise StopIteration()

            if s.__end and s.__sc.at(caret) == s.__end:
                raise StopIteration()

            if s.__sc.csize(caret) != len(s):
                raise Exception('Invalid fastbin chunk size')

        elif s.__type == Chunk.TYPE_TOP:
            raise Exception('Top chunk is not iterable')

        elif s.__type == Chunk.TYPE_LEFT:
            caret = s.__chunk
            ptr = s.__chunk.cast(s.__sc.ptr_t)

            while True:
                if ptr <= s.__end: raise StopIteration()

                ptr -= s.__sc.OFFSET
                caret = ptr.cast(s.__sc.type_t)

                if s.__sc.fits(caret):
                    break

        else:
            raise Exception('Unknown chunk type=%i' % s.__type)

        s.__chunk = caret
        s.__validate__(fence = True)

        return s

    next = __next__

    def is_gap(s): return s.__sc.fence(s.__chunk)
