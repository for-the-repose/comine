#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from time   import time

from comine.iface.heap  import IHeap
from comine.core.mapper import Mapper, Singleton, log
from comine.core.trace  import trace_write


class Sticker(type):
    def __init__(cls, name, kl, kw):
        super(Sticker, cls).__init__(name, kl, kw)

    def __call__(cls, *kl, **kw):
        inst = HeMan().get(cls.__who__(), meta = False)

        if inst and not isinstance(inst, cls):
            raise TypeError('HeMan() gave invalid heap instance')

        return inst or super(Sticker, cls).__call__(*kl, **kw)


class Heap(IHeap):
    __metaclass__  = Sticker


class HeMan(object):
    __metaclass__ = Singleton

    def __init__(s):
        s.__ready   = False
        s.__heaps   = {}
        s.__found   = []
        s.__mapper  = Mapper()

    def disq(s, force = False):
        s.__mapper = Mapper()

        for name, heap in s.__heaps.items():
            if heap._Inst__disq(force = force) is True:
                log(1, 'discovered heap %s' % name)

        s.__ready = True

    def lookup(s, at):  #  -> { (impl, IHeap.lookup(at)) }
        for impl in s.enum():
            result = impl.lookup(at)

            if result[0] not in (IHeap.REL_OUTOF, IHeap.REL_UNKNOWN):
                yield (impl, result)

    def enum(s, all = False, meta = False):
        def _pre(z): return all or z.__ready__()

        def _get(z): return z if meta else z.__impl__()

        return map(_get, filter(_pre, s.__heaps.values()))

    def get(s, name, meta = False):
        heap = s.__heaps.get(name)

        if heap is not None:
            return heap if meta else heap.__impl__()

    def __str__(s):
        return 'HeMan(%u heaps, %s)' % (len(s.__heaps),)

    def __push(s, cls):
        if issubclass(cls, IHeap):
            name = getattr(cls, '__who__')()

            inst = s.__heaps.get(name)

            if inst and inst.__cls__ != cls:
                log(1, 'heap %s already registered' % name)

            elif not inst:
                s.__heaps[name] = _Inst(cls, s.__mapper, log)

                log(1, 'registered new heap %s' % name)

        else:
            log(1, 'unknown heap impl %s' % str(cls))

    @staticmethod
    def register(cls):
        HeMan().__push(cls)

        return cls


class _Inst(object):
    def __init__(s, cls, mapper, log):
        s.__cls     = cls
        s.__mapper  = mapper
        s.__log     = log

        s.__reset()

    def __cls__(s):     return c.__cls

    def __who__(s):     return s.__cls.__who__()

    def __impl__(s):
        return s.__impl if s.__impl else None

    def __ready__(s):
        return s.__impl.__ready__() if s.__impl else s.__impl

    def __hist__(s, level = 8, join = False):
        "# gives discovery log as { (rel_time, level, line) }"

        it = filter(lambda z: z[1] <= level, s.__hist)

        return '\n'.join(it) if join is True else it

    def __tb__(s):      return s.__tb

    def __when__(s):    return (s.__start, s.__end)

    def __disq(s, force = False):
        if not s.__ready__() or force is True:
            s.__reset()

            s.__start   = int(time())

            try:
                s.__impl = s.__cls(log = s.__pass, mapper = s.__mapper)

            except Exception as E:
                tb, s.__impl = [], False

                s.__log(1, "heap impl %s raised with '%s'"
                               % (s.__cls.__who__(), str(E)))

                trace_write(lambda x: tb.append(x), extended = True)

                s.__tb = ''.join(tb)

            finally:
                s.__end = int(time())

            return s.__ready__()

    def __reset(s):
        s.__start   = None
        s.__end     = None
        s.__impl    = None
        s.__hist    = []    # heap discovery log, (level, string)
        s.__tb      = None  # formatted traceback on disq error

    def __pass(s, lev, line):
        if s.__impl is None:
            s.__hist.append((int(time()) - s.__start, lev, line))

        s.__log(lev, line)


__init__ = (HeMan, IHeap, Heap)
