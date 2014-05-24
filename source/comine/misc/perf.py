#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from time       import time
from cProfile   import Profile
from pstats     import Stats
from StringIO   import StringIO

class Perf(object):
    @classmethod
    def timed(s, func):
        def _wrap(*kl, **kw):
            start = time()

            try:
                return func(*kl, **kw)

            finally:
                spent   = '%0.2f' % (time() - start)
                flit    = '%s(%s, %s)' % (func.__name__, kl, kw)

                print 'perf: %s() -> %s' % (flit, spent)

        return _wrap

    @classmethod
    def profile(s, func):
        def _wrap(*kl, **kw):
            prof = Profile()
            prof.enable()

            try:
                return func(*kl, **kw)

            finally:
                prof.disable()
                result = StringIO()

                ps = Stats(prof, stream = result).sort_stats('cumulative')
                ps.print_stats()

                print result.getvalue()

        return _wrap
