#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from struct import pack

from comine.core.iheap  import IHeap
from comine.core.heman  import HeMan
from comine.misc.humans import Humans, From

class cmd_heap(gdb.Command):
    def __init__(s):
        gdb.Command.__init__(s, "heap",
                    gdb.COMMAND_OBSCURE,
                    gdb.COMPLETE_NONE,
                    True)


class cmd_heap_discover(gdb.Command):
    ''' Discover all heaps structures '''

    def __init__(s):
        gdb.Command.__init__(s, "heap disq", gdb.COMMAND_OBSCURE)

    def invoke(s, args, tty):
        s.dont_repeat()

        argv = (args or 'do').split()

        sub, argv = argv[0], (argv[1:] if len(argv) > 1 else [])

        if sub == 'status':
            if len(argv) != 0:
                raise Exception('unhandled args=%s' % argv)

            for heap in HeMan().enum(all = True, meta = True):
                s.__show_disq_status(heap)

        elif sub == 'log':
            s.__do_for_heap(argv, s.__show_disq_log)

        elif sub == 'tb':
            s.__do_for_heap(argv, s.__show_disq_tb)

        elif sub not in ('do', 'force'):
            raise Exception('invalid arg %s' % args)

        else:
            HeMan().disq(force = (args == 'force'))

    def __do_for_heap(s, argv, do, *kl, **kw):
        if len(argv) > 1:
            raise Exception('unhandled args=%s' % argv[1:])

        elif len(argv) == 1:
            heap = HeMan().get(argv[0])

            if heap is None:
                print 'heap %s not registered' % argv[0]

            else:
                do(heap, *kl, **kw)
        else:
            for heap in HeMan().enum(all = True, meta = True):
                do(heap, *kl, **kw)

    def __show_disq_status(s, heap):
        smap = { None : 'UNK', True : 'RDY', False : 'FAIL' }

        state   = smap.get(heap.__ready__(), '?')
        rg      = heap.__when__()

        if rg.count(None) < 1:
            when    = Humans.time(rg[0])
            take    = ' +' + Humans.delta(rg[1] - rg[0])

        else:
            when, take = '', ''

        print '%-8s -> %-6s %s%s' \
                % (heap.__who__(), state, when, take)

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


class cmd_heap_lookup(gdb.Command):
    ''' Lookup address at heap '''

    def __init__(s):
        gdb.Command.__init__(s, "heap lookup", gdb.COMMAND_OBSCURE)

    def invoke(s, args, tty):
        s.dont_repeat()

        argv = args.split()

        alit, argv = argv[0], (argv[1:] if len(argv) > 1 else [])

        kw, at  = {}, int(str(alit) or '0', 0)

        if len(argv) == 1 and argv[0] == 'dump':
            kw['dump'] = True

        elif len(argv) > 0:
            raise Exception('unknown args=%s' % argv)

        cmd_heap_lookup._lookup(at, **kw)

    @staticmethod
    def _lookup(at, ident = '', dump = None):
        for impl, (rel, aligned, offset, size, gran) in HeMan().lookup(at):
            rlit = IHeap.REL_NAMES.get(rel, '?%u' % rel)
            slit = '' if size is None else (', %ub' % size)
            gran = '' if gran is None else (' ~%ub' % gran)

            print '%simpl %s -> %s 0x%x %+i%s%s' \
                        % (ident, impl.__who__(), rlit,
                            aligned, offset, slit, gran)

            if dump is not None and size:
                raw = Mapper().readvar(aligned, size, gdbval = False)

                print Humans.hexdump(raw,  ident = len(ident) + 2)


class cmd_maps(gdb.Command):
    def __init__(s):
        gdb.Command.__init__(s, "maps",
                    gdb.COMMAND_OBSCURE,
                    gdb.COMPLETE_NONE,
                    True)

    def invoke(s, args, tty):
        s.dont_repeat()

        argv = args.split()

        sub, argv = argv[0], (argv[1:] if len(argv) > 1 else [])

        if sub == 'list':
            kw = {}

            if len(argv) == 2 and argv[0] == 'larger':
                kw['larger'] = From.bytes(argv[1])

            elif len(argv) != 0:
                raise Exception('unknown args %s' % argv)

            for rg, _, _, trg  in Mapper().enum(**kw):
                print Humans.region(rg), trg

        elif sub == 'find':
            look_heap = False;

            if len(argv) == 2 and argv[1] == 'heap':
                look_heap = True

            elif len(argv) != 1:
                raise Exception('Invalid args=%s' % argv)

            sub = pack('Q',  int(argv[0], 0))

            for seq, (rg, at) in enumerate(Mapper().search(sub)):
                print "%2u: %x, +%x, [%x, %x) %s" \
                        % (seq, at, at - rg[0], rg[0], rg[1], Humans.region(rg))

                if look_heap is True:
                    cmd_heap_lookup._lookup(at, '  ')

        else:
            raise Exception('unknown command %s' % sub)


for x in [cmd_heap, cmd_heap_lookup, cmd_heap_discover, cmd_maps]: x()
