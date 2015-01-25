
from time   import time, localtime, strftime
from re     import match

class Humans(object):
    @staticmethod
    def bytes(value):
        v, ex = value, True
        pref = ['b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb', 'zb', 'yb']

        def _f(v, x):
            return ('%.3f' % v)[:4] + pref[x]

        if v < 1024: return '%ib' % v

        for x in xrange(1, len(pref)):
            q, v = (v & 0x3ff, v >> 10)

            if v & 0x3ff == v:
                if v & 0x200: continue

                return _f(v + q / 1024., x)

    @staticmethod
    def delta(time):
        scale = [('s', 60.), ('min', 60.), ('hour', 24.), ('day', 7.),
                    ('week', 4.), ('month', 52.), ('year', None) ]

        for pref, div in scale:
            if not div or time < div:
                return '%0.1f%s' % (time, pref)

            else:
                time /= div

    @staticmethod
    def region(rg):
        return Humans.bytes(rg[1] - rg[0])

    @staticmethod
    def time(when):
        return strftime('%Y-%m-%d %H:%M:%S', localtime(when))

    @staticmethod
    def ago(stamp):
        return Humans.delta(time() - stamp)


class From(object):
    __BI_SCALE = { None : 0, 'k' : 10, 'm':  20, 'g': 30, 't' : 40,
                    'p' : 50, 'e' : 60, 'z' : 70, 'y' : 80 }

    @classmethod
    def bytes(cls, line):
        return cls.items(line, suff = 'b')

    @classmethod
    def items(cls, line, suff = ''):
        g = match('((?:\d+\.?)?(?:\.\d+)?)(\w+)?', line.strip())

        if g is None:
            raise ValueError('Invalid value literal %s' % line)

        else:
            g = g.groups()

            val = int(g[0] or '1')

            if g[1] is None:
                return val

            elif not g[1].endswith(suff):
                raise ValueError('unknown suffix %s' % g[1])

            else:
                suff = g[1][:len(g[1]) - len(suff)]

                if suff in cls.__BI_SCALE:
                    return val * (1 << cls.__BI_SCALE[suff])

                else:
                    raise ValueError('unknown suffix %s' % g[1])
