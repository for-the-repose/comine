#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.ring   import Ring
from comine.maps.tools  import Tools
from comine.misc.types  import Types
from comine.misc.humans import Humans
from .errors            import ErrorChunk
from .scale             import Scale
from .chunk             import Chunk
from .exten             import EHeap
from .defs              import Flags

class Guess(object):
    def __init__(s, log, world, ring, sc = None):
        s.__log     = log
        s.__world   = world
        s.__ring    = Types.ensure(ring, Ring)
        s.__sc      = Types.ensure(sc, Scale, True)

    def __call__(s):
        it = [('left', s.__extend_lefts),
                ('mmaps', s.__search_mmaped) ]

        found = sum(map(lambda x: s.run(*x), it))

    def run(s, name, call):
        change = s.__ring.measure(call)

        s.__log(1, 'found %s in %i frags while %s disq' %
                (Humans.bytes(change[1]), change[0], name))

        return change[1]

    def __extend_lefts(s):
        '''
            Invoke left traverse procedure for each known heap block that
            is known not to be closed on left side. This code has any sense
            only for primary arena that my be not a contigous.
        '''

        if len(s.__ring) > 0: s.__extend_left_do()

    def __extend_left_do(s):
        def _extend(span):
            place = s.__ring.wider(span.__rg__()[0]-1)

            if place is not None:
                for rg, spans in s.__world.physical(place):
                    if rg[1] == place[1]: return rg, spans

            return None, None

        s.__log(8, 'try to left extends on %s' % Tools.str(s.__ring.bound()))

        with s.__ring.begin(auto = True) as trans:
            for span in s.__ring.enum(pred = EHeap.pred(EHeap.TAG_FRAG)):
                left, spans = _extend(span)

                if left is not None:
                    new = s.__traverse_left(rg = left)

                    if new is not None:
                        arena = span.exten().__arena__()

                        exten = EHeap(arena, tag = EHeap.TAG_LEFT)

                        trans.make(rg = new, exten = exten)

    def __traverse_left(s, rg):
        '''
            Try to resolve range at left from an alias point. There is
            no way to traverse exactly chunks from right to left. Some
            heruistic logic must be used here to find candidates for
            left continuations. This hints may be useful:

            1. All chunks are aligned to two Scale.__atom__() bytes,
                thus align mask is 0x3 for 32bit space and 0x7 for x86_64.

            2. Chunks in left continuation all must be marked used as
                all free chunks are known from bin lists and it is
                already accounted as heap known regions.

            3. Only chunks of primary arena may be founded in continuations
                since all secondary arenas is contigous and w/o any holes.
        '''

        last, nodes = rg[1], { rg[1]: [] }

        fmask = Flags.MMAPPED | Flags.NON_MAIN_ARENA

        for caret in Chunk(s.__sc, rg[1], Chunk.TYPE_LEFT, end = rg[0]):
            probe = caret.__at__()

            if last - probe > 1024*1024: break

            if caret.flag(fmask):       continue

            if len(caret) > 1024*1024:  continue

            links = nodes.get(probe + len(caret))

            if links is not None:
                links.append(probe)

                nodes[probe] = []
                last = probe

        left = s.__resolve_left(rg[1], nodes)

        return (left, rg[1] )if left < rg[1] else None

    def __resolve_left(s, at, nodes):
        ''' Analyse tree build while left traverse and give estimated
            left boundary for region.
        '''

        while True:
            childs = nodes.get(at)

            if childs is None:
                raise Exception('invalid left tree')

            if len(childs) == 0:
                return at

            if len(childs) > 1:
                return at

            at = childs[0]

    def __search_mmaped(s):
        '''
            Useful hints for mmaped regions search:

            1. For fragments allocated by mmap() in fallback mode exists
                minimum size and it is equal to 1mb.

            2. The beginning of allocated region by mmap() probably would
                be aligned by page size, typical is 4kb, recorded in the
                heap.

            3. Chunks in mmaped regions must be marked as used since its
                being unmmaped on free() call and isn't collected in any
                free lists.
        '''

        with s.__ring.begin(auto = True) as trans:
            def _push(place):
                exten = EHeap(tag = EHeap.TAG_MMAPPED)

                trans.make(rg = place, exten = exten)

            for place, spans in s.__world.physical(None, unused = s.__ring):
                last, thresh = None, place[0]

                for chunk in s.__mmaped_pages(place):
                    if thresh <= chunk.__at__():
                        if last is not None: _push(last)

                        last = chunk.__rg__()

                    else:
                        last = None

                    thresh = max(thresh, (last or (0,thresh))[1])

                if last is not None: _push(last)

    def __mmaped_pages(s, place):
        page = s.__sc.__page__()

        _align = lambda x, m = page - 1: (x + m) ^ ((x + m) & m)

        if Tools.len(place) > 64 * 1024:
            for at in xrange(_align(place[0]), place[1], page):
                try:
                    chunk = Chunk(s.__sc, at, Chunk.TYPE_REGULAR)

                    if chunk.flag(Flags.MMAPPED):
                        if Tools.inside(place, chunk.__rg__()):
                            yield chunk

                except ErrorChunk as E:
                    pass
