
from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/generic', '/heaps' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

from mapper import Mapper 
from heap   import TheGlibcHeap

mapper = Mapper()

