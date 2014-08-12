#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.iface.bugs  import IBug
from comine.misc.types  import Singleton, Types
from comine.gdb.tools   import Tools

class Bugs(object):
    __metaclass__ = Singleton

    def __init__(s):
        s.__bugs    = set()
        s.__tools   = Tools()

    def __push(s, bug):
        s.__bugs.add(bug)

    def check(s):
        runtime = s.__tools.version()

        if runtime is not None:
            name, ver, left = runtime

            for bug in s.__bugs:
                inst = bug()

                by, on = inst.__ver__()

                if by != name:
                    pass

                elif on[0] and on[0] > ver:
                    pass

                elif on[1] and on[1] < ver:
                    pass

                else:
                    yield inst

    @classmethod
    def register(cls, bug):
        Bugs().__push(Types.ensure(bug, IBug))

        return bug


@Bugs.register
class _GdbPyLeaks(IBug):
    def __ver__(s):
        return 'gdb', (None, (7, 5, 0))

    def __short__(s):
        return 'python bindings memory leaks'
