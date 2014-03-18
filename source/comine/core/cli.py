#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from struct import pack

from comine.iface.heap  import IHeap
from comine.iface.maps  import IMaps
from comine.core.heman  import HeMan
from comine.core.flat   import Flatten
from comine.core.world  import World
from comine.core.base   import ECore
from comine.maps.tools  import Tools
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

        if not s.__route(sub, argv):
            raise Exception('unknown command %s' % sub)

    def __route(s, sub, argv):
        cmd = getattr(s, '_cmd_maps__sub_maps_' + sub, None)

        if cmd is not None:
            try:
                cmd(argv)

            except Exception as E:
                raise

            else:
                return True

    def __sub_maps_use(s, argv):
        if len(argv) != 1:
            raise Exception('path to maps file required')

        Mapper().attach(argv[0])

    def __sub_maps_ring(s, argv):
        world = Mapper().__world__()

        for rec in world:
            plit = rec.__prov__() or ''

            print " %2u %8s %s" \
                    % (rec.__seq__(), plit, rec.__ring__())

    def __sub_maps_walk(s, argv):
        if len(argv) != 1:
            raise Exception('give ring number')

        ring = Mapper().__world__().by_seq(seq = int(argv[0]))

        print ring

        for span in ring:
            print '  ', span

    def __sub_maps_flat(s, argv):
        short = not(argv and argv[0] == 'full')

        it = Flatten(Mapper().__world__())

        for seq, (rg, spans, cov) in enumerate(it):
            cont = '%u spans' % len(spans)
            size    = Humans.region(rg)
            place   = Tools.str(rg, digits = 16)

            if seq > 0 and not short: print

            print '-rg=%s %8s %0.2f %0.2f %s' \
                    % ((place, size) + cov + (cont,))

            if short is False:
                spans.sort(key = lambda x: x.__rg__()[0])

                for span in spans:
                    is_core = isinstance(span.exten(), ECore)
                    rlit    = Tools.str(span.__rg__(), digits = 16)
                    slit    = 'Core' if is_core else 'Span'

                    print ' | %s %s' % (slit, rlit)

                    if not is_core:
                        print '  + %s' % (span.desc(prep = ''), )

    def __sub_maps_find(s, argv):
        look_heap = False;

        if len(argv) == 2 and argv[1] == 'heap':
            look_heap = True

        elif len(argv) != 1:
            raise Exception('Invalid args=%s' % argv)

        blob = pack('Q',  int(argv[0], 0))

        it = Mapper().__world__().search(blob)

        for seq, (at, offset, span) in enumerate(it):
            rg = span.__rg__()

            print "%2u: %016x, +%08x, %s" \
                    % (seq, at, offset, span)

            if look_heap is True:
                cmd_heap_lookup._lookup(at, '  ')

    def __sub_maps_lookup(s, argv):
        if len(argv) != 1:
            raise Exception('give only one arg with address')

        world = Mapper().__world__()

        for offset, rec, span in world.lookup(int(argv[0], 0)):
            print '  %+06x  %s' % (offset, span)

    def __sub_maps_save(s, argv):
        if len(argv) != 2:
            raise Exception('path to maps file required')

        world = Mapper().__world__()

        entity = world.by_path(argv[0])

        if entity is None:
            print 'cannot locate span by path %s' % argv[0]

        else:
            res = world.save(entity, argv[1], padd = False)

            if res is not None:
                elit = entity.__class__.__name__

                print 'dumped %s -> (%u ch, %s data, %s padd)' \
                        % (elit, res[0],
                            Humans.bytes(res[1]),
                            Humans.bytes(res[2]))

    def __sub_maps_show(s, argv):
        if len(argv) != 1:
            raise Exception('give one of unused, conflict')

        kind =  ('unused', 'conflict', 'virtual')

        if argv[0] in kind:
            kw = dict([(argv[0], True)])

        elif argv[0] == 'all':
            kw = dict(map(lambda x: (x, True), kind))

        else:
            raise Exception('unknown class=%s' % argv[0])

        world = Mapper().__world__()

        ulits = {
            World.USAGE_UNUSED : 'free',
            World.USAGE_CONFLICT : 'confl',
            World.USAGE_VIRTUAL : 'virt' }

        def _dsingle(rg, spans):
            if len(spans) == 1:
                span = spans[0]

                if span.__rg__() == rg:
                    exten = span.exten()

                    return 'Span' if exten is None else exten.__desc__()

                else:
                    return str(span)

            elif len(spans) > 1:
                return '%u spans' % len(spans)

            else:
                return '-'

        for kind, rg, phys, logic in world.enum(**kw):
            ulit    = ulits.get(kind, '?%x' % kind)
            size    = Humans.region(rg)

            if kind == World.USAGE_UNUSED:
                desc = _dsingle(rg, phys)

            elif kind == World.USAGE_VIRTUAL:
                desc = _dsingle(rg, logic)

            elif kind == World.USAGE_CONFLICT:
                desc = _dsingle(rg, logic)

            else:
                desc = '?'

            print '  %5s %8s %s %s' \
                    % (ulit, size, Tools.str(rg, digits=16), desc)

    def __qry_lang(s, argv):
        if len(argv) == 2 and argv[0] == 'larger':
            kw['larger'] = From.bytes(argv[1])

            if kw['larger'] is None:
                raise ValueError('cannot convert %s to bytes' % argv[1])


for x in [cmd_heap, cmd_heap_lookup, cmd_heap_discover, cmd_maps]: x()
