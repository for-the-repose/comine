#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.heap  import IHeap
from comine.cline.lib   import CLines
from comine.cline.lang  import CFail, Eval, Addr
from comine.misc.humans import Humans
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
        s.__do_for_heap(heman, argv.next(), s.__show_disq_log)

    def __sub_heap_trace(s, heman, argv):
        s.__do_for_heap(heman, argv.next(), s.__show_disq_tb)

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
            print " | %02s: %s" % (when, line)

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
    def _lookup(heman, at, ident = '', dump = None):
        for impl, (rel, aligned, offset, size, gran) in heman.lookup(at):
            line = IHeap.desc(rel, aligned, offset, size, gran)

            print '%simpl %s -> %s' % (ident, impl.__who__(), line)

            if dump and size:
                dump = size if dump is True else min(size, (dump + 15) & ~15)

                raw = heman.__infer__().readvar(aligned, dump, gdbval = False)

                print Humans.hexdump(raw,  ident = len(ident) + 2)

                if dump < size:
                    print '  --- %ub shown, %ub left' % (dump, size - dump)

    def __sub_heap_enum(s, heman, argv):
        comb, it = None, heman.get().enum()

        if argv:
            if len(argv) < 2:
                raise CFail('at least one more arg required')

            token, value, over, = argv.pop(0), int(argv.pop(0)), None

            if argv:
                if len(argv) < 2:
                    raise CFail('at least one more arg required')

                if argv[0] != 'over':
                    raise CFail('unexpected keyword %s' % argv[0])

                over = int(argv[1])

            if token == 'min':
                comb = Limit(min, value, key = lambda x: x[2])

            elif token == 'max':
                comb = Limit(max, value, key = lambda x: x[2])

            elif token == 'some':
                comb = SomeOf(value, over = over)

        for rel, at, size, gran in (comb or (lambda x: x))(it):
            print IHeap.desc(rel, at, 0, size, gran)

        if comb is not None:
            print '-- limited, seen %u chunks' % comb.__seen__()
