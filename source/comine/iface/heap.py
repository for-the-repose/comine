#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.world import IOwner

class IHeap(IOwner):
    REL_UNKNOWN = 0;    REL_OUTOF   = 1;    REL_ZERO    = 2
    REL_KEEP    = 3;    REL_FREE    = 4;    REL_CHUNK   = 5
    REL_HUGE    = 6;    REL_HEAD    = 7;    REL_INTERN  = 8
    REL_WASTE   = 9;    REL_MAYBE   = 10;

    IGNORE = (REL_OUTOF, REL_UNKNOWN)

    REL_NAMES = { REL_OUTOF : 'outof', REL_ZERO : 'zero',
                    REL_KEEP : 'keep', REL_FREE : 'free',
                    REL_CHUNK : 'chunk', REL_HUGE  : 'huge',
                    REL_HEAD: 'head', REL_INTERN : 'intrn',
                    REL_WASTE : 'waste', REL_MAYBE : 'maybe' }

    def __init__(s, log, infer):
        '''
            Heap disq module init call. Heap manager pass

            log     logging functor log(lev, msg), used for logging
                    any debug and info messaages. This output may be
                    filtered and preserved by manager;

            infer   Infer() object to which heap manager was attached.
                    Heap disq module should do all its discovery only
                    in this inferior;
        '''

        IOwner.__init__(s)

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

    def lookup(s, at):    # -> (rel, aligned, offset, size, gran)
        '''
            Should return tuple of (rel, aligned, offset, size, gran)
            if supplied at address falls to some heap managed memory
            block or None in other cases. Possible block utilization
            should be pointed by rel member:

                REL_OUTOF   address is not falls to any known heap
                            parts. The rest of args should be None;

                REL_ZERO    preallocated but still never used memory
                            block. May not hold any usefull data that
                            was released some time ago by heap.

                REL_KEEP    already used by heap impl block but now
                            unused and keeped for later reusage. May
                            hold some useful data with unknown scheme.

                REL_FREE    recently released but probably still valid
                            memory chunk. Should not be damaged by a
                            heap impl after free() call including any
                            changes in chunk size;

                REL_CHUNK   a valid allocated small memory chunk.
                            Usually  storage is taken from some big
                            partitioned and shared with another small
                            chunks memory block;

                REL_MAYBE   Probable candidate for REL_CHUNK case but
                            exact judment is not possible with current
                            level of discovered data;

                REL_HUGE    a valid allocated huge memory chunk. Usually
                            single mmap() call used for allocating block
                            for that chunk and its data mostly occupies
                            it;

                REL_HEAD    falls to some internal part of partitioned
                            data block that belongs to valid allocated
                            small or huge chunk.

                REL_INTERN  falls to some internal part of partitioned
                            data block that is not related with any of
                            allocated chunks.

                REL_WASTE   occupied but unused area.

            Requested at address should be splittted to aligned and
            offset parts, thus

                at := aligned + offset

            Aligned logic context is given by its relation type.

            Chunk size for relations [ REL_CHUNK, REL_HUGE, REL_FREE ]
            is passed in two fields size and gran. size member holds
            allocated space and gran allocation granularity. Thus actual
            requested allocation chunk size falls in range

                used := (size - gran, size]

            gran member has no any meanings for other relations, thus
            should be set to None by impls and not used by caller.
        '''

        raise Exception('not impl')

    def emum(s, rg = None, pred = None, huge = None):
        '''
            Yields all known heap chunks using rules:

                1. Do not pass chunks thrown by pred functor, which is
                    provided by IPred inrerface;

                2. Limit iteration only over a optionally supplied rg
                    bytes range in address space;

                3. Pass only REL_HUGE chunks if huge is set to True;

                4. Pass only (REL_CHUNK, REL_MAYBE) if huge is False;

                5. Pass all allocated chunks if huge is set to None;
        '''

        raise Exception('not impl')


class IPred(object):
    '''
        Heap chunk filter predicate functor. Used as

        with func(align) as F:
            ...

            if func.__prec__(srange):
                ...

                for it in some_generator():
                    meta = (rel, at, size, delta)

                    if func(*meta) is True: yield meta

        where align is upper rounding functor to next align size point
        used in heap impl. Every used size must be prepared according
        to aligment or predicate should use delta arg in checks.
    '''

    __slots__  = tuple()

    def __prec__(s, rg):
        '''
            Precondition test, heap impl gives sizes range that may be
            passed to __call__() method while iteration over chunks.
            Call should return False if any size in this region will
            never give True result on __call__(s, ,size, ..) invocation.

            Precondition helps to terminate enumerate early with invalid
            filters passed to enum(() call.
        '''

        return True

    def __call__(s, rel, at, size, delta):
        raise Exception('not implemented')

    def begin(s, align):
        raise Exception('not implemented')

    def __enter__(s):
        raise Exception('not implemented')

    def __exit__(s, Et, Ev, tb):
        raise Exception('not implemented')
