#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from struct import pack

from comine.cline.lib   import CLines
from comine.cline.lang  import CFail, Eval, Addr
from comine.iface.heap  import IHeap
from comine.mine.revix  import Revix
from comine.mine.index  import Index, Locate

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
