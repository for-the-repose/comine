#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from os         import environ, listdir
from os.path    import abspath, isdir
from imp        import load_source
from sys        import path, modules

from comine.core.logger import log
from comine.core.trace  import location
from comine.misc.types  import Singleton

class Plugs(object):
    __metaclass__ = Singleton

    def __init__(s):
        s.__ready   = False

    def load(s, force = False):
        if not s.__ready:
            from comine.heaps.glibc	import TheGlibcHeap
            from comine.cline.heap  import CHead
            from comine.cline.world import CWorld
            from comine.cline.mine  import CMine

            s.__ready = True

        s.__plugs(force = force)

    def __plugs(s, force = False):
        plugs =  environ.get('COMINE_PLUGS')

        if plugs is not None:
            if not isdir(plugs):
                log(1, 'plugs path "%s" is not a directory')

            else:
                s.__plug_lib(plugs)

                for fname in filter(Plugs.__is_pname, listdir(plugs)):
                    s.__plug_load(plugs, fname, force)

    def __plug_lib(s, base):
        lpath = abspath(base)

        if lpath not in path:
            path.insert(0, lpath)

    def __plug_load(s, path, fname, force = False):
        path    = path + '/' + fname
        name    = Plugs.__plug_name(fname)
        desc    = None

        if force or name not in modules:
            try:
                module = load_source(name, path)

            except Exception as E:
                loc = location()

                desc = 'at %s:%u %s' % (loc[1:] + (str(E),))

            finally:
                result = 'FAIL' if desc else 'OKEY'

                log(2, 'loading plug %s <- %s' % (result, name))

                if desc:
                    log(3, ' | %s' % desc)

    @classmethod
    def __is_pname(cls, name):
        if not name.endswith('.py'):
            pass

        elif name == '__init__.py':
            pass

        elif name.count('.') > 1:
            pass

        elif name.startswith('_'):
            pass

        else:
            return True

    @classmethod
    def __plug_name(cls, name):
        suffix = name[:-3] if name.endswith('.py') else name

        return '' + suffix
