
from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

try:
    from gdb import PYTHONDIR

except Exception as E:
    pass

else:
    from comine.core.mapper import Mapper
    from comine.heaps.glibc	import TheGlibcHeap

    mapper = Mapper()

