#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from gdb    import execute, Inferior, selected_inferior

from comine.iface.infer import ILayout
from comine.misc.types  import Types

class Tools(object):
    __slots__ = ('_Tools__space', '_Tools__gin', '_Tools__exec')

    def __enter(func):
        def _wrap(tool, *kl, **kw):
            with tool():
                return func(tool, *kl, **kw)

        return _wrap

    def __init__(s, gin = None):
        s.__gin     = Types.ensure(gin, Inferior, none = True)
        s.__exec    = execute

    def __gin__(s):     return s.__gin

    def __sel__(s):     return selected_inferior()

    def __call__(s):
        if s.__gin is None:
            raise Exception('tools has no attached infer')

        return _Enter(s)

    def call(s, cmd):
        return s.__exec(cmd, to_string = True)

    def version(s):
        for line in s.call('show version').split('\n'):
            m = match('GNU gdb \([^)]+\) (.+)', line)

            if m is not None:
                g = match('(\d+)\.(\d+)\.(\d+)?(.*)', m.group(1))

                if g is not None:
                    ver = tuple(map(int, g.groups()[:3]))

                    return ('gdb', ver, g.group(4))

    @__enter
    def attach(s, pid):
        pid = Types.ensure(pid, int)

        s.call('attach %u' %pid)

    @__enter
    def load(s, layout):
        layout = Types.ensure(layout, ILayout)

        if layout.__root__() is not None:
            debug = '%s/usr/lib/debug' % layout.__root__()

            s.call('set solib-absolute-prefix %s' %  layout.__root__())
            s.call('set debug-file-directory %s' % debug)

        s.call('set auto-load safe-path /')
        s.call('file %s' % layout.__binary__())
        s.call('core-file %s' % layout.__core__())

    def switch(s, num):
        s.call('inferior %u' % Types.ensure(num, int))

        assert s.__sel__().num == num

    def make(s):
        ''' Make an empty infer '''

        raise Exception('Not implemented')


class _Enter(object):
    __slots__ = ('_Enter__tools', '_Enter__was')

    def __init__(s, tools):
        s.__tools   = tools
        s.__was     = None

    def __enter__(s):
        sel = s.__tools.__sel__()
        gin = s.__tools.__gin__()

        if sel is None or sel != gin:
            s.__was = sel

            s.__tools.switch(gin.num)

        else:
            s.__was = None

    def __exit__(s, Et, Ev, tb):
        if s.__was is not None:
            s.__tools.switch(s.__was.num)

            s.__was = None
