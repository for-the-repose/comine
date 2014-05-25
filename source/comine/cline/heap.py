#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.heap  import IHeap
from comine.cline.lib   import CLines
from comine.misc.humans import Humans

@CLines.register
class CHead(CLines):
    def __init__(s):
        invoke = lambda x, y, z: x(y.__heman__(), z)

        CLines.__init__(s, 'heap', invoke)

    def __sub_heap_disq(s, heman, argv):
        argv = argv or [ 'do' ]

        sub, argv = argv[0], argv[1:]

        if sub == 'status':
            if len(argv) != 0:
                raise Exception('unhandled args=%s' % argv)

            for heap in heman.enum(all = True, meta = True):
                s.__show_disq_status(heap)

        elif sub == 'log':
            s.__do_for_heap(heman, argv, s.__show_disq_log)

        elif sub == 'tb':
            s.__do_for_heap(heman, argv, s.__show_disq_tb)

        elif sub not in ('do', 'force'):
            raise Exception('invalid arg %s' % argv)

        else:
            heman.disq(force = ((argv and argv[0]) == 'force'))

    def __do_for_heap(s, heman, argv, do, *kl, **kw):
        if len(argv) > 1:
            raise Exception('unhandled args=%s' % argv[1:])

        elif len(argv) == 1:
            heap = heman.get(argv[0])

            if heap is None:
                print 'heap %s not registered' % argv[0]

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
        alit, argv = argv[0], (argv[1:] if len(argv) > 1 else [])

        kw, at  = {}, int(str(alit) or '0', 0)

        if len(argv) == 1 and argv[0] == 'dump':
            kw['dump'] = True

        elif len(argv) > 0:
            raise Exception('unknown args=%s' % argv)

        CHead._lookup(heman, at, **kw)

    @staticmethod
    def _lookup(heman, at, ident = '', dump = None):
        for impl, (rel, aligned, offset, size, gran) in heman.lookup(at):
            rlit = IHeap.REL_NAMES.get(rel, '?%u' % rel)
            slit = '' if size is None else (', %ub' % size)
            gran = '' if gran is None else (' ~%ub' % gran)

            print '%simpl %s -> %s 0x%x %+i%s%s' \
                        % (ident, impl.__who__(), rlit,
                            aligned, offset, slit, gran)

            if dump is not None and size:
                raw = heman.__infer__().readvar(aligned, size, gdbval = False)

                print Humans.hexdump(raw,  ident = len(ident) + 2)
