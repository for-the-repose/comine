#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.heap  import IHeap
from comine.cline.lib   import CLines
from comine.cline.lang  import CFail, Eval, Addr, Items
from comine.heaps.pred  import HRange
from comine.misc.humans import Humans
from comine.misc.dump   import Dump
from comine.misc.limit  import Limit, SomeOf


@CLines.register
class CHead(CLines):
    def __init__(s):
        invoke = lambda x, y, z: x(y.__heman__(), z)

        CLines.__init__(s, 'heap', invoke)

    def __sub_heap_disq(s, heman, argv):
        heman.disq(force = (argv.next() == 'force'))

    def __sub_heap_status(s, heman, argv):
        if argv.next() is not None:
            raise CFail('too much args passed')

        for heap in heman.enum(all = True, meta = True):
            s.__show_disq_status(heap)

    def __sub_heap_log(s, heman, argv):
        s.__do_for_heap(heman, argv, s.__show_disq_log)

    def __sub_heap_trace(s, heman, argv):
        s.__do_for_heap(heman, argv, s.__show_disq_tb)

    def __do_for_heap(s, heman, argv, do, *kl, **kw):
        name = argv.next()

        if name and argv.next() is not None:
            raise CFail('too much args passed')

        elif name is not None:
            heap = heman.get(name)

            if heap is None:
                print 'heap %s not registered' % name
            else:
                do(heap, *kl, **kw)
        else:
            for heap in heman.enum(all = True, meta = True):
                do(heap, *kl, **kw)

    def __show_disq_status(s, heap):
        smap = { None : 'UNK', True : 'RDY', False : 'FAIL' }

        state   = smap.get(heap.__ready__(), '?')
        rg      = heap.__when__()
        name    = heap.__who__()

        if rg.count(None) < 1:
            when    = Humans.time(rg[0])
            take    = ' +' + Humans.delta(rg[1] - rg[0])
        else:
            when, take = '', ''

        print '%-8s -> %-6s %s%s' % (name, state, when, take)

    def __show_disq_log(s, heap, level = 8):
        when    = Humans.time(heap.__when__()[0])
        ago     = Humans.ago(heap.__when__()[0])

        print '+heap %s discovery log, begin at %s (%s ago)' \
                    % (heap.__who__(), when, ago)

        for when, level, line in heap.__hist__(level):
            print " | %03s: %s" % (when, line)

    def __show_disq_tb(s, heap):
        if heap.__tb__() is not None:
            print heap.__tb__()

    def __sub_heap_lookup(s, heman, argv):
        _Prev = lambda x: None if x == 'all' else int(x, 0)

        qry = {
                0: (-1, None),

                1: (-1, (Addr, 2, ('at',)) ),
                2: (0, [ ('dump', 3, ('dump', 256)) ] ),
                3: (0, (_Prev, 0, ('dump',)) )
        }

        CHead._lookup(heman, **Eval(qry)(argv))

    @staticmethod
    def _lookup(heman, at, ident = '', dump = False):
        for impl, (rel, aligned, offset, size, gran) in heman.lookup(at):
            line = IHeap.desc(rel, aligned, offset, size, gran)

            print '%simpl %s -> %s' % (ident, impl.__who__(), line)

            rg = (aligned, aligned + size)

            if dump is not False:
                Dump(heman.__infer__(), True, dump)(rg, len(ident))

    def __sub_heap_enum(s, heman, argv):
        qry = {
                0: (-1, None),

                #_ kind of chunks selector
                1: (2, [
                        ('huge', 2, ('huge', True)),
                        ('small', 2, ('huge', False)) ]),

                #_ chunk size selector
                2: (4, [ ('ge', 3, None)] ),
                3: (-1, (Items, 4, ('ge',)) ),
                4: (6, [ ('lt', 5, None)] ),
                5: (-1, (Items, 6, ('lt',)) ),

                #_ sampling range limiter
                6: (8, [ ('over', 7, None)]),
                7: (-1, (Items, 8, ('over',)) ),

                #_ some items selector
                8: (10, [
                        ('max', 9, ('aggr',)),
                        ('min', 9, ('aggr',)),
                        ('some', 9, ('aggr',))]),
                9: (-1, (Items, 10, ('show',)) ),

                #_ dump selector
                10: (0, [ ('dump', 11, ('dump', True)) ]),
                11: (-1, (Items, 0, ('dump',)))
        }

        kw = Eval(qry)(argv)

        comb, pred, dump = None, None, None

        if 'ge' in kw or 'lt' in kw:
            pred = HRange(rg = (kw.get('ge'), kw.get('lt')))

        if 'aggr' in kw:
            if kw.get('aggr') == 'min':
                comb = Limit(min, kw['show'], key = lambda x: x[2])

            elif kw.get('aggr') == 'max':
                comb = Limit(max, kw['show'], key = lambda x: x[2])

            elif kw.get('aggr') == 'some':
                comb = SomeOf(kw['show'], over = kw.get('over'))

        if 'dump' in kw:
            limit = 256 if kw['dump'] is True else kw['dump']

            dump = Dump(heman.__infer__(), True, limit)

        it = heman.get().enum(pred = pred, huge = kw.get('huge', None))

        for rel, at, size, gran in (comb or (lambda x: x))(it):
            print IHeap.desc(rel, at, 0, size, gran)

            if dump is not None:
                dump(rg = (at, at + size), ident = 2)

                print ''

        if comb is not None:
            print '-- limited, seen %u chunks' % comb.__seen__()
