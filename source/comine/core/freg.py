#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from bisect         import bisect_right

from comine.misc.func   import gmap


class Freg(object):
    ''' Fast addr regs lookup object '''

    def __init__(s, regs, model, gran = 0):
        regs = Freg.__glide(regs, gran)

        s.__start   = list(map(lambda x: x[0], regs))
        s.__end     = [None] + list(map(lambda x: x[1], regs))

        s.__fn = getattr(s, '_Freg__do_' + model, s.__do_basic)

    def make(s):
        '''
            Cannot do exta calls inside predicate function just
            because python is incredibly slow crap. Either cannot
            overload __call__ method while __init__() as py doesn't
            allow do this for __call__() method.

            This is why this ugly method exists and Freg() class.
        '''

        return s.__fn

    @classmethod
    def __glide(cls, regs, gran):
        regs.sort()

        out = [ (0, 0) ]

        for z in xrange(len(regs)):
            assert out[-1][0] <= regs[z][0]

            if out[-1][1] + gran >= regs[z][0]:
                out[-1] = (out[-1][0], regs[z][1])

            else:
                out.append(regs[z])

        assert out[0] == (0, 0)

        return out[1:]

    def __len__(s): return len(s.__start)

    def bytes(s):
        return sum(gmap(lambda rg: rg[1] - rg[0], s.enum()))

    def enum(s):
        for z in xrange(len(s.__start)):
            yield (s.__start[z], s.__end[z + 1])

    def __do_basic(s, at):
        z = bisect_right(s.__start, at)

        return z > 0 and at < s.__end[z]

    def __do_amd64(s, at):
        if not (0x0000800000000000 <= at < 0xffff800000000000):
            z = bisect_right(s.__start, at)

            return z > 0 and at < s.__end[z]
