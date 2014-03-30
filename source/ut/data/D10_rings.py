#!/usr/bin/env python2

from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/../' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

from comine.maps.tools  import Rinf, Tools
from comine.maps.span   import Span
from comine.maps.ring   import Ring
from comine.maps.dump   import dump


_r_rg_1_1 = [
        (0x000, 0x100), (0x400, 0x500),
        (0x600, 0x800), (0xb00, 0xc00),
        (0xd00, 0xe00) ]

_r_rg_1_2 = [
        (0x100, 0x400), (0x510, 0x580),
        (0x700, 0x900), (0xb00, 0xc20),
        (0xd00, 0xe00), (0xe80, 0xf00) ]

_r_rg_1_3 = [
        (0xb00, 0xc20), (0xd80, 0xf00) ]


_r_rg_2_1 = [
        (0x600, 0x680), (0x700, 0x780),
        (0xa00, 0xc10), (0xd50, 0xf00) ]

should_plain = [
    (0,     (None,  0x000),     0),
    (1,     (0x000, 0x100),     1),
    (2,     (0x100, 0x100),     0), # brake
    (3,     (0x100, 0x400),     1),
    (4,     (0x400, 0x400),     0), # brake
    (5,     (0x400, 0x500),     1),
    (6,     (0x500, 0x510),     0),
    (7,     (0x510, 0x580),     1),
    (8,     (0x580, 0x600),     0),
    (9,     (0x600, 0x700),     1),
    (10,    (0x700, 0x800),     2),
    (11,    (0x800, 0x900),     1),
    (12,    (0x900, 0xb00),     0),
    (13,    (0xb00, 0xc00),     3),
    (14,    (0xc00, 0xc20),     2),
    (15,    (0xc20, 0xd00),     0),
    (16,    (0xd00, 0xd80),     2),
    (17,    (0xd80, 0xe00),     3),
    (18,    (0xe00, 0xe80),     1),
    (19,    (0xe80, 0xf00),     2),
    (20,    (0xf00, Rinf),      0),
]

should_group = [
    (0,     (None,  0x000),     0),
    (1,     (0x000, 0x100),     1),
    (2,     (0x100, 0x100),     0), # brake
    (3,     (0x100, 0x400),     1),
    (4,     (0x400, 0x400),     0), # brake
    (5,     (0x400, 0x500),     1),
    (6,     (0x500, 0x510),     0),
    (7,     (0x510, 0x580),     1),
    (8,     (0x580, 0x600),     0),
    (9,     (0x600, 0x900),     2),
    (10,    (0x900, 0xb00),     0),
    (11,    (0xb00, 0xc20),     3),
    (12,    (0xc20, 0xd00),     0),
    (13,    (0xd00, 0xf00),     4),
    (14,    (0xf00, Rinf),      0),
]

should_isect_change = [
    (0,     (None,  0x700),     0),
    (1,     (0x700, 0x800),     2),
    (2,     (0x800, 0xb00),     0),
    (3,     (0xb00, 0xc00),     3),
    (4,     (0xc00, 0xc20),     2),
    (5,     (0xc20, 0xd00),     0),
    (6,     (0xd00, 0xd80),     2),
    (7,     (0xd80, 0xe00),     3),
    (8,     (0xe00, 0xe80),     0),
    (9,     (0xe80, 0xf00),     2),
    (10,    (0xf00, Rinf),      0),
]

should_isect_group = [
    (0,     (None,  0x700),     0),
    (1,     (0x700, 0x800),     2),
    (2,     (0x800, 0xb00),     0),
    (3,     (0xb00, 0xc20),     3),
    (4,     (0xc20, 0xd00),     0),
    (5,     (0xd00, 0xe00),     3),
    (6,     (0xe00, 0xe80),     0),
    (7,     (0xe80, 0xf00),     2),
    (8,     (0xf00, Rinf),      0),
]


one, two, three, four = map(Ring, [_r_rg_1_1, _r_rg_1_2,
									_r_rg_1_3, _r_rg_2_1])

_get = lambda ring, at: ring.lookup(at)[1]

_make = lambda it: dict(map(lambda x:(_get(*x[0]), x[1]), it))


should_isect_object = _make([
        ((one, 0x600),   [ (0x700, 0x800) ]),
        ((two, 0x700),   [ (0x700, 0x800) ]),
        ((one, 0xb00),   [ (0xb00, 0xc00) ]),
        ((two, 0xb00),   [ (0xb00, 0xc20) ]),
        ((three, 0xb00), [ (0xb00, 0xc20) ]),
        ((one, 0xd00),   [ (0xd00, 0xe00) ]),
        ((two, 0xd00),   [ (0xd00, 0xe00) ]),
        ((three, 0xd80), [ (0xd80, 0xe00), (0xe80, 0xf00) ]),
        ((two, 0xe80),   [ (0xe80, 0xf00) ]) ])


should_isect_oneby_true = _make([
        ((one, 0x600),   [ (0x600, 0x680), (0x700, 0x780)]),
        ((two, 0x700),   [ (0x700, 0x780) ]),
        ((one, 0xb00),   [ (0xb00, 0xc00) ]),
        ((two, 0xb00),   [ (0xb00, 0xc10) ]),
        ((three, 0xb00), [ (0xb00, 0xc10) ]),
        ((one, 0xd00),   [ (0xd50, 0xe00) ]),
        ((two, 0xd00),   [ (0xd50, 0xe00) ]),
        ((three, 0xd80), [ (0xd80, 0xf00) ]),
        ((two, 0xe80),   [ (0xe80, 0xf00) ]) ])


should_isect_oneby_false = _make([
        ((one, 0x000),   [ (0x000, 0x100) ]),
        ((two, 0x100),   [ (0x100, 0x400) ]),
        ((one, 0x400),   [ (0x400, 0x500) ]),
        ((two, 0x510),   [ (0x510, 0x580) ]),
        ((one, 0x600),   [ (0x680, 0x700), (0x780, 0x800)]),
        ((two, 0x700),   [ (0x780, 0x900) ]),
        ((two, 0xb00),   [ (0xc10, 0xc20) ]),
        ((three, 0xb00), [ (0xc10, 0xc20) ]),
        ((one, 0xd00),   [ (0xd00, 0xd50) ]),
        ((two, 0xd00),   [ (0xd00, 0xd50) ]) ])
