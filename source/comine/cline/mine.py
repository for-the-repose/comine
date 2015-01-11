#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from struct import pack

from comine.cline.lib   import CLines
from comine.cline.lang  import CFail, Eval, Addr
from comine.iface.heap  import IHeap
from comine.mine.revix  import Revix
from comine.mine.index  import Index, Locate
from comine.mine.trace  import Trace, Clect
from comine.mine.lost   import Lost, Walk
from comine.misc.humans import Humans


@CLines.register
class CMine(CLines):
    def __init__(s):
        CLines.__init__(s, 'mine')

    def __sub_mine_revix(s, infer, argv):
        if argv.next() is not None:
            raise CFail('command does not accept args')

        if infer.__layout__() is None:
            raise CFail('layout with core required')

        Revix(infer).build()

    def __sub_mine_reget(s, infer, argv):
        qry = {
                0: (-1, None),

                1: (-1, (Addr, 2, ('at',)) ),
                2: (0, (str, 3, ('end',)) ),
                3: (0, [
                        ('heap', 0, ('heap', True)) ])
        }
 
        kw = Eval(qry)(argv)

        rg, end = kw['at'], kw.get('end')

        if end is not None:
            if end[0] == '+':
                rg = (rg, rg + int(end[1:]))

            else:
                rg = (rg, int(end, 0))

        heap = kw.get('heap') and infer.__heman__().get()
 
        index = Locate(infer)

        for at, refer in index.lookup(rg):
            if heap:
                some = heap.lookup(refer)

                if some is not None:
                    line = IHeap.desc(*some)

                    print '  0x%x <- %s' % (at, line)

            else:
                print "  0x%x <- 0x%x" % (at, refer)

    def __sub_mine_lost(s, infer, argv):
        terms = Lost.terminals(infer.__world__())

        print('found %s terminals in %u regs'
                % (Humans.bytes(terms.bytes()), len(terms)))

        save = infer.__layout__().special('cache') + '/lost.chunks'
        heap = infer.__heman__().get()
        lost = Lost(heap, Locate(infer), terms.make(), cache = 2**20)

        Walk(save)(lost, it = heap.enum())

    def __sub_mine_trace(s, infer, argv):
        at      = int(argv.next(), 0)
        offset  = int(argv.next())

        print "Tracing chunk 0x%x +0%x" % (at, offset)

        index = Locate(infer)
        trace = Trace(infer, at, offset)

        for seq, at, desc, fall in trace():
            span = ' '.join(map(lambda x: '+0x%x %s' % x, fall))

            print ' | %02u 0x%x %-8s %s' %  (seq, at, desc, span)

            s.__show_occurance(infer.__world__(), index, rg = (at, at + 1))

    def __sub_mine_anno(s, infer, argv):
        addr = int(argv.next(), 0)
        mask = int(argv.next() or '0', 0) 

        it = enumerate(Clect(infer)(addr, mask))

        for seq, (di, rel, at, off, size, gran) in it:
            rlit = IHeap.REL_NAMES.get(rel, '?%u' % rel)

            print('  #%02u +%04u -> %6s 0x%012x +%4u %8ub ~%ub'
                    % (seq, di, rlit, at, off, size, gran))

    def __show_occurance(s, world, index, rg):
        def _enum():
            for at, ref in index.lookup(rg):
                for offset, _, span in world.lookup(ref):
                    yield (at, ref, offset, span)

        for seq, (at, ref, offset, span) in enumerate(_enum()):

            print "    - %2u: %016x, +%08x, %s" % (seq, ref, offset, span)
