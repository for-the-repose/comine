#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from struct import pack

from comine.iface.heap  import IHeap
from comine.core.world  import World, Pred
from comine.core.space  import Space
from comine.mine.revix  import Emit
from comine.misc.humans import Humans

class Clect(object):
    def __init__(s, infer):
        world = infer.__world__()

        s.__heap    = infer.__heman__().get()

        if s.__heap is None:
            raise Exception('Heap is not discovered')

        s.__emit    = Emit(infer, world.addrs(gran = 7).make())

    def __call__(s, at, mask = 0x0):
        rel, at, _, size, _  = s.__heap.lookup(at)

        if rel in (IHeap.REL_CHUNK, IHeap.REL_HUGE):
            for some in s.__enum(rg = (at, at + size), mask = mask):
                yield some

    def __enum(s, rg, mask):
        for to, di in s.__emit(rg):
            if di & mask == 0:
                rel, at, off, size, gran  = s.__heap.lookup(to)

                if rel in (IHeap.REL_CHUNK, IHeap.REL_HUGE):
                    yield (di - rg[0], rel, at, off, size, gran)


class Trace(object):
    def __init__(s, infer, at, offset):
        s.__libc    = infer.__libc__()
        s.__world   = infer.__world__()
        s.__at      = at
        s.__offset  = offset
        s.__seq     = 0
        s.__trace   = dict()
        s.__next    = at

    def __call__(s):
        while s.__next is not None:
            if s.__next == 0:
                yield (s.__seq, s.__next, 'nullptr', [])

            else:
                falls = list(s.__check(s.__next))
                seen = s.__seen(s.__next)

                addr_t = s.__libc.std_type('addr_t')
                pptr_t = s.__libc.std_type('ptr_t').pointer()

                if len(falls) == 0:
                    yield (s.__seq, s.__next, 'invalid', falls)

                elif seen is not None:
                    yield (s.__seq, s.__next, 'loop %u' % seen, falls)

                else:
                    yield (s.__seq, s.__next, 'next', falls)

                    val = gdb.Value(s.__next + s.__offset).cast(pptr_t)

                    s.__push(int(val.dereference().cast(addr_t)))

                    continue

            s.__push(None)

    def __check(s, at):
        rg = (at + s.__offset, at + s.__offset + 8)

        for offset, rec, span in s.__world.lookup(at):
            if Pred.phys(span) and span.is_inside(rg):
                yield (offset, span)

    def __push(s, at):
        if s.__next is not None:
            s.__trace[s.__next] = s.__seq

        s.__seq     +=1
        s.__next    = at

    def __seen(s, at):
        if at is not None or at != 0:
            return s.__trace.get(at)
