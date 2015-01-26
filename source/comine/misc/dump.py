#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.walk   import Walk
from comine.maps.tools  import Tools
from comine.misc.humans import Humans
from comine.misc.func   import yrange


class Dump(object):
    def __init__(s, infer, zero = False, limit = None):
        s.__infer   = infer
        s.__bpl     = 16
        s.__zero    = None
        s.__limit   = limit

        if zero is True:
            s.__zero = infer.__world__().by_prov('zero')

    def __call__(s, rg, ident = 0):
        limit = s.__round(rg, s.__limit)

        zero, frags, left, last = 0, 0, 0, None

        walk = Walk(rings = s.__zero or [])

        for on, spans in walk.change(rg, empty = True):
            size = Tools.len(on)

            if spans and limit > 0:
                print '  ----- collapsed %ub of zero pages' % size

            elif spans:
                last = size; zero += size; frags += 1

            elif limit > 0:
                place = (on[0], on[0] + min(limit, size))

                used = s.__piece(place, ident, rg[0])

                limit -= used; left += size - used

            else:
                last = None; left += size

        if zero + left > 0: s.__stats(left, zero, last, frags)

    def __stats(s, left, zero, last, frags):
        lelit = Humans.bytes(left + zero)
        zelit = Humans.bytes(zero)

        if s.__zero:
            print '          @left %s, %u zpages in %s, on tail %s' \
                            % (lelit, frags, zelit, Humans.bytes(last or 0))

        else:
            print '          @left %s, has no zpages info' % lelit

    def __round(s, rg, limit):
        limit = limit and int((limit + s.__bpl - 1) / s.__bpl) * s.__bpl

        return (rg[1] - rg[0]) if limit is None else limit

    def __piece(s, rg, ident, base = 0, block = 2 ** 14):
        for at in yrange(*(rg + (block,))):
            blob = s.__read(at, size = min(block, rg[1] - at))

            print s.__dump(blob, ident + 2, off = at - base),

        return Tools.len(rg)

    def __read(s, at, size):
        return s.__infer.readvar(at, size, gdbval = False)

    def __dump(s, raw, ident = 0, off = 0):
        out = []

        total = (len(raw) + s.__bpl - 1) / s.__bpl

        for ln in xrange(total):
            out.append(' ' * ident)
            out.append('%5.5x ' % (off + ln * s.__bpl,))

            line = raw[ln * s.__bpl: (ln + 1) * s.__bpl]

            for y in xrange(len(line)):
                out.append(' %02.2x' % ord(line[y]))

                if y == 7:
                    out.append(' ')

            out.append('   ' * (max(0, s.__bpl - y - 1)))
            out.append('  ')

            for y in xrange(len(line)):
                if 0x1f < ord(line[y]) < 0x80:
                    out.append(line[y])
                else:
                    out.append('.')

            out.append('\n')

        return ''.join(out)
