#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from os             import rename
from os.path        import isdir, exists
from itertools      import chain
from re             import match

from comine.iface.world import IOwner
from comine.core.logger import log
from comine.maps.ring   import Ring
from comine.misc.humans import Humans
from comine.misc.func   import gmap, yrange
from comine.misc.perf   import Perf


class Zeroes(IOwner):
    def __init__(s, infer):
        s.__world   = infer.__world__()
        s.__lay     = infer.__layout__()
        s.__emit    = Zero(infer)

        s.__ring = (s.__world.by_prov('zero') or [None])[0]

    def load(s):
        if s.__ring is None:
            base = s.__lay.special('cache')

            target = base + '/zero.ring'

            if not exists(target):
                s.__build(base + '/~zero.ring', target)

            s.__ring = Ring()

            def _parse(line):
                g = match('([\da-f]+) ([\da-f]+)', line.strip())

                if g is not None:
                    return tuple(map(lambda x: int(x, 16), g.groups()))

            with open(target, 'r') as F:
                for place in gmap(_parse, F):
                    s.__ring.make(rg = place)

            s.__world.push(s, s.__ring, provide = 'zero')

    def __build(s, temp, target):
        with open(temp, 'w') as ou:
            count, total, zero = s.__walk(ou.write)

        rename(temp, target)

        print '-found %u zero rg in %s over %s' \
                    % (count,
                        Humans.bytes(zero),
                        Humans.bytes(total))

    def __walk(s, save):
        count, total, zero = 0, 0, 0

        for span in s.__spans():
            total += len(span)

            for place in s.__emit(span):
                save('%016x %016x\n' % place)

                zero += place[1] - place[0]
                count += 1

        return count, total, zero

    def __spans(s):
        it = s.__world.physical(None, bins = True)

        return sorted(list(set(chain(*gmap(lambda x: x[1], it)))))


class Zero(object):
    def __init__(s, infer, page = 4096):
        s.__infer   = infer
        s.__mask    = page - 1

        assert s.__mask & page == 0x0

    def __call__(s, span):
        caret = None

        for at, used in s.__enum(rg = span.__rg__()):
            if not used:
                caret = at if caret is None else caret

            elif caret is not None:
                yield (caret, at)

                caret = None

    def __enum(s, rg):
        rg = ((rg[0] + s.__mask) & ~s.__mask, rg[1] & ~s.__mask)

        if rg[0] < rg[1]:
            for at in yrange(*(rg + (s.__mask + 1,))):
                size = min(s.__mask + 1, rg[1] - at)

                blob = s.__infer.readvar(at, size, False)

                yield at, s.__check(blob)

            yield rg[1], True

    def __check(s, blob):
        for z in (blob or '\xff'):
            if z != '\0': return True

        return False
