#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from time   import time

from comine.iface.heap  import IHeap
from comine.core.trace  import trace_write
from comine.core.logger import log
from comine.misc.types  import Types, Singleton
from comine.misc.segen  import Scn, ScnRef

class _Plugs(object):
    __metaclass__ = Singleton

    def __init__(s):
        s.__scn     = Scn()
        s.__heaps   = {}

    def __scn__(s):     return int(s.__scn)

    def enum(s):        return s.__heaps.itervalues()

    def push(s, cls):
        if issubclass(cls, IHeap):
            name = getattr(cls, '__who__')()

            meta = s.__heaps.get(name)

            if meta and meta.__cls__() != cls:
                log(1, 'heap %s already registered' % name)

            elif not meta:
                s.__scn.alter()
                s.__heaps[name] = _Meta(cls)

                log(1, 'registered new heap %s disq plug' % name)

        else:
            log(1, 'unknown heap impl %s' % str(cls))


class HeMan(object):
    def __init__(s, mapper):
        s.__heaps   = {}
        s.__mapper  = mapper
        s.__ref     = ScnRef(_Plugs())
        s.__log     = log

        s.sync(force = True)

    def __str__(s):
        return 'HeMan(%s, %u heaps)' \
                    % (s.__ref.__desc__(), len(s.__heaps))

    def __infer__(s):   return s.__mapper

    def sync(s, force = False):
        if not s.__ref.valid() or force:
            used = set(s.__heaps.keys())

            for meta in _Plugs().enum():
                inst = s.__heaps.get(meta.__who__())

                if inst is not None:
                    used.remove(meta.__who__())

                else:
                    inst = _Inst(meta, s.__mapper, s.__log)

                    s.__heaps[meta.__who__()] = inst

            for name in used:
                inst = s.__heaps.pop(name)

            return True

    def disq(s, force = False):
        s.sync()

        for name, heap in s.__heaps.items():
            if heap._Inst__disq(force = force) is True:
                log(1, 'discovered heap %s' % name)

    def lookup(s, at):  #  -> { (impl, IHeap.lookup(at)) }
        for impl in s.enum():
            result = impl.lookup(at)

            if result and result[0] not in IHeap.IGNORE:
                yield (impl, result)

    def enum(s, all = False, meta = False):
        def _pre(z): return all or z.__ready__()

        def _get(z): return z if meta else z.__impl__()

        return map(_get, filter(_pre, s.__heaps.values()))

    def get(s, name, meta = False):
        heap = s.__heaps.get(name)

        if heap is not None:
            return heap if meta else heap.__impl__()

    @staticmethod
    def register(cls):
        _Plugs().push(cls)

        return cls


class _Meta(object):
    __slots__ = ('_Meta__cls', '_Meta__name')

    def __init__(s, cls):
        s.__cls     = Types.ensure(cls, IHeap)
        s.__name    = cls.__who__()

    def __cls__(s):     return s.__cls

    def __who__(s):     return s.__name

    def __call__(s, *kl, **kw):
        return s.__cls(*kl, **kw)


class _Inst(object):
    def __init__(s, meta, mapper, log):
        s.__meta    = meta
        s.__mapper  = mapper
        s.__log     = log

        s.__reset()

    def __meta__(s):    return s.__meta

    def __who__(s):     return s.__meta.__who__()

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
                s.__impl = s.__meta(log = s.__pass, mapper = s.__mapper)

            except Exception as E:
                tb, s.__impl = [], False

                s.__log(1, "heap impl %s raised with '%s'"
                               % (s.__meta.__who__(), str(E)))

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


__init__ = (HeMan, IHeap)
