#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class IHeap(object):
    REL_UNKNOWN = 0;    REL_OUTOF   = 1;    REL_ZERO    = 2
    REL_KEEP    = 3;    REL_FREE    = 4;    REL_CHUNK   = 5
    REL_HUGE    = 6;    REL_HEAD    = 7;    REL_INTERN  = 8

    REL_NAMES = { REL_OUTOF : 'outof', REL_ZERO : 'zero',
                    REL_KEEP : 'keep', REL_FREE : 'free',
                    REL_CHUNK : 'chunk', REL_HUGE  : 'huge',
                    REL_INTERN : 'intrn' }

    @classmethod
    def __who__(s):     # -> str
        "Should provide name of heap impl"

        raise Exception('not impl')

    def __ready__(s):   # -> True | False | None
        '''
            Should return heap status in following scheme
                True    -> discovered and ready;
                False   -> heap discover failed;
                None    -> not yet discovered, usually detected
                            by HeMan() instance holder;
        '''

        raise Exception('not impl')

    def lookup(s, at):    # -> (rel, aligned, offset, size)
        '''
            Should return tuple of (rel, aligned, offset, size) if
            supplied at address falls to some heap managed memory
            block or None in other cases. Possible block utilization
            should be pointed by rel member:

                REL_OUTOF   address is not falls to any known heap parts.
                            The rest of return args should be None;

                REL_ZERO    preallocated but still never used memory
                            block. May not hold any usefull data that
                            was released some time ago.

                REL_KEEP    already used by heap impl block but now
                            unused and keeped for later reusage. May
                            hold some useful data with unknown scheme.

                REL_FREE    recently released but probably still valid
                            memory chunk. Should not be damaged by a
                            heap impl after free() call including any
                            changes in chunk size;

                REL_CHUNK   a valid allocated small memory chunk. Usually
                            storage is taken from some big partitioned and
                            shared with another small chunks memory block;

                REL_HUGE    a valid allocated huge memory chunk. Usually
                            single mmap() call used for allocating block
                            for that chunk and its data mostly occupies it;

                REL_HEAD    falls to some internal part of partitioned
                            data block that belongs to valid allocated
                            small or huge chunk.

                REL_INTERN  falls to some internal part of partitioned
                            data block that is not related with any of
                            allocated chunks.

            Requested at address should be splittted to aligned and
            offset parts, thus at = aligned + offset. Aligned logic
            context is given by its relation type.
        '''

        raise Exception('not impl')

    def emum(s):
        raise Exception('not impl')
