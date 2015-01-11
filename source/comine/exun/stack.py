#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.gdb.thread  import Threads
from comine.core.world  import Pred
from comine.iface.world import IOwner
from comine.maps.exten  import IExten
from comine.maps.ring   import Ring, Span
from comine.maps.tools  import Tools
from comine.misc.humans import Humans


class Stack(IOwner):
    def __init__(s, log, infer):
        s.__log     = log
        s.__ring    = Ring(props = [ ('used', Stack.__fn_used) ])

        world   = infer.__world__()
        threads = Threads(infer.__tools__())

        stacks  = s.__discover(threads, world)

        s.__log(1, "located %s in %u stack regs, %s used"
                    % (Humans.bytes(s.__ring.__bytes__()),
                        len(s.__ring),
                        Humans.bytes(s.__ring.prop('used'))))

        world.push(s, s.__ring, provide = 'stack')

    @classmethod
    def __fn_used(cls, ring):
        pred = EStack.pred(tag = EStack.TAG_USED)

        return sum(ring.enum(pred = pred, conv = len))

    def __discover(s, threads, world):
        with s.__ring.begin(auto = True) as trans:
            stats = [0, 0]  # no_spans, too_many

            for seq, (thr, sp) in enumerate(threads.enum()):
                spans = list(world.lookup(sp, pred = Pred.phys))

                if len(spans) == 0:
                    stats[0] += 1

                elif len(spans) > 1:
                    stats[1] += 1

                else:
                    s.__span_push(trans, spans[0][2], thr, sp)

            if stats.count(0) != len(stats):
                s.__log(7, "stack bugs none=%u, mult=%u" % tuple(stats))

            return seq + 1

    def __span_push(s, trans, span, thr, sp):
        for tag, place in s.__span_split(span, sp):
            if Tools.len(place) > 0:
                trans.make(place, exten = EStack(thr, tag))

    def __span_split(s, span, sp):
        yield (EStack.TAG_FREE,  (span.__rg__()[0], sp))

        yield (EStack.TAG_USED, (sp, span.__rg__()[1]))


class EStack(IExten):
    __slots__ = ('_EStack__thr', '_EStack__tag')

    TAG_USED    = 1
    TAG_FREE    = 2

    __NAMES = { TAG_USED: 'used', TAG_FREE: 'free' }

    def __init__(s, thr, tag, *kl, **kw):
        IExten.__init__(s, *kl, **kw)

        s.__thr     = thr
        s.__tag     = tag

    def __tag__(s):     return s.__tag

    def __desc__(s):
        tlit = EStack.__NAMES.get(s.__tag, '?%u' % s.__tag)

        return 'EStack(#%u, %s)' % (s.__thr, tlit)

    def __ident__(s):
        return (s.__class__.__name__, EStack.__NAMES.get(s.__tag))

    def __args__(s, rg):
        kl, kw = IExten.__args__(s, rg)

        return ((s.__thr, s.__tag) + kl, kw)

    def extend(s, rg, force = False):
        return True

    @classmethod
    def pred(cls, tag):
        if tag is not None:
            return lambda span: span.exten().__tag__() == tag
