#!/usr/bin/env python2

from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/../', '/../../' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

from comine.maps.tools  import Tools
from comine.maps.span   import Span
from comine.maps.alias  import Alias
from comine.maps.ring   import Ring
from comine.maps.dump   import dump
from comine.maps.walk   import Walk

class Op(object):
    def __init__(s, fn, kl, res):
        s.__fn      = fn
        s.__kl      = kl
        s.__res     = res

    def __call__(s):
        res = getattr(Tools, s.__fn)(*s.__kl)

        return res == s.__res, (s.__res, res)


wild = (None, None)

_PROG = [
    Op('isect', kl = [ (None, 10), (-10, None) ], res =  (-10, 10)),
    Op('isect', kl = [ (0, 10), (5, 20) ],  res =  (5, 10)),
    Op('isect', kl = [ (0, 10), (10, 20) ], res = None),
    Op('isect', kl = [ wild, wild], res = wild),
    Op('isect', kl = [ wild, (0, 10)], res = (0, 10)),
    Op('isect', kl = [ wild, (0, 0)], res = (0,  0)),
    Op('inside', kl = [ wild, wild], res = True),
    Op('inside', kl = [ wild, (None, 0)], res = True),
    Op('inside', kl = [ wild, (0, None)], res = True),
    Op('inside', kl = [ wild, (-5, 5)], res = True),
    Op('inside', kl = [ (0, 10), (5, 10)], res = True),
    Op('inside', kl = [ (0, 10), (5, 20)], res = False),
    Op('inside', kl = [ (0, 10), (10, 20)], res = False),
    Op('inside', kl = [ (0, 10), (10, 11)], res = False),
    Op('extend', kl = [ (5, 10), (0, 20), 0], res = (5, 10)),
    Op('extend', kl = [ (5, 10), (0, 20), Tools.LEFT], res = (0, 10)),
    Op('extend', kl = [ (5, 10), (0, 20), Tools.RIGHT], res = (5, 20)),
    Op('extend', kl = [ (5, 10), (0, 20), Tools.BOTH], res = (0, 20)),
    Op('extend', kl = [ wild, (0, 20), Tools.LEFT], res = (0, 20)),
    Op('extend', kl = [ (None, 10), (0, 20), Tools.LEFT], res = (0, 10)),
    Op('extend', kl = [ (5, None), (0, 20), Tools.RIGHT], res = (5, 20)),
    Op('extend', kl = [ (5, 10), (0, None), Tools.RIGHT], res = (5, None)),
    Op('extend', kl = [ (5, 10), wild, Tools.RIGHT], res = (5, None)),
    Op('extend', kl = [ (5, 10), wild, Tools.BOTH], res = wild),
    Op('empty', kl = [ (0,0) ], res = True),
    Op('empty', kl = [ (0, 10) ], res = False),
    Op('empty', kl = [ (10, 0) ], res = None),
    Op('empty', kl = [ (None, None) ], res = False),
    Op('empty', kl = [ (None,  0)  ], res = False),
    Op('empty', kl = [ (1, None) ], res = False)
]


def test_map_range():
    for op in  _PROG:
        print op()


def rest_map_ring_split():
    ring = Ring()

    ring.make(rg = (0x000, 0x400))
    ring.make(rg = (0x400, 0x800))

    dump(ring)


def test_map_span():
    ring = Ring()

    exten = Alias([-16, 0, 10, 0x700, 2048])
    span = Span(rg = (None, None), exten = exten)

    print ring
    print span

    parts = span.split(rg = 0, flags = Span.KEEP_ALL)

    print parts

    parts = span.split(rg = (0, 0x800), flags = Span.KEEP_ALL)

    print parts

    self = parts[1][1]

    ring.push(self)

    print ring

    parts = self.replace((0x200, 0x600), Span.KEEP_DROP)

    ring.push(Span(rg = (0x2000, 0x2200)))

    print parts

    dump(ring)

    print Tools.str(ring.wider(place = 0x400))
    print Tools.str(ring.wider(place = 0x3000))
    print Tools.str(ring.wider(place = (0x600, 0x800)))
    print Tools.str(ring.wider(place = (0x601, 0x7ff)))
    print Tools.str(ring.wider(place = (None, 0x800)))

    span = ring.lookup(0x700)[1]

    span.extend(where = -1, to = 0x500)

    dump(ring)

    wild = Span(rg = (None, None))

    cu01 = wild.cut(at = 0, keep = Span.KEEP_AFTER)
    cu02 = wild.cut(at = 0x100, keep = Span.KEEP_AFTER)
    cu03 = wild.cut(at = 0x800, keep = Span.KEEP_BEFORE)

    print wild, cu01, cu02, cu03

    rest = wild.cut(at = 0x800, keep = Span.KEEP_AFTER)

    print rest, wild, wild.__len__()


def test_map_place():
    ring = Ring()

    ring.make(rg = (0x000, 0x100))
    ring.make(rg = (0x400, 0x500))
    ring.make(rg = (0x600, 0x800))

    place = ring.place(place = (None, None))

    for span in place:
        print 'FL', span

    for span in reversed(place):
        print 'FR', span

    place = ring.place(place = (0x010, 0x500))

    for span in place:
        print 'CT', span


if __name__ == '__main__':
    test_map_range()
    rest_map_ring_split()
    test_map_span()
    test_map_place()
