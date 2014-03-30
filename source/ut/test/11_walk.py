#!/usr/bin/env python2

from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/../', '/../../' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

from comine.maps.tools  import Tools, Rinf
from comine.maps.span   import Span
from comine.maps.ring   import Ring
from comine.maps.dump   import dump
from comine.maps.walk   import Walk, Diff, OneBy
from comine.maps.aggr   import Change, Group, Align
from comine.maps.join   import _Join, _Tag

from data.D10_rings		import *

class Expect(object):
    def __init__(s, call, should):
        s.__call    = call
        s.__should  = should

    def __call__(s, aggr, rg, sub = None):
        empty, brake, cuts = aggr.__args__()

        pred = lambda x: brake if Tools.empty(x[1]) else (empty or x[2] > 0)

        should = s.__subset(sub)

        it = s.__term(s.__call(aggr, rg), end = (None, []))
        ex = s.__term(should, pred, end = (None, None, 0))

        for check, (rg, its) in zip(ex, it):
            if check[1] != rg or check[2] != len(its):
                l_rg, r_rg = map(Tools.str, [rg, check[1]])

                raise Exception('at %u %s got=%s' % (check[0], r_rg, l_rg) )

    def __subset(s, rg = None):
        rg = rg or (None, None)

        start = 0 if rg[0] is None else rg[0]
        end = len(s.__should) if rg[1] is None else rg[1]

        return iter(s.__should[start:end])

    def __term(s, it, pred = lambda x: True, end = None):
        for z in filter(pred, it): yield z

        yield end

    def run(s, prog):
        for tag, aggr, kl, kw in prog:
            yield tag

            s(aggr(*kl), **kw)

    def dump(s, aggr, rg):
        for seq, (place, spans) in enumerate(s.__call(aggr, rg)):
            brake   = Tools.empty(place) and not spans
            desc    = ' brake' if brake else ''

            print '- %2u %s%s' % (seq, Tools.str(place), desc)

            for span in spans or []:
                print '      | %s' % (str(span), )


def test_map_change():
    test = Expect(Walk(rings = [one, two, three]), should_plain)

    prog = [
        ('01', Change, (True, True),    { 'rg' : (None, None)} ),
        ('02', Change, (True, False),   { 'rg' : (None, None)} ),
        ('03', Change, (False, True),  { 'rg' : (None, None)} ),
        ('04', Change, (False, False),   { 'rg' : (None, None)} ),
        ('05', Change, (False, False),
                { 'rg' : (0x100, None), 'sub' : (2, None)} ),
    ]

    for it in test.run(prog): yield it

def test_map_group():
    test = Expect(Walk(rings = [one, two, three]), should_group)

    prog = [
        ('01', Group, (True, True),    { 'rg' : (None, None)} ),
        ('02', Group, (True, False),   { 'rg' : (None, None)} ),
        ('03', Group, (False, True),  { 'rg' : (None, None)} ),
        ('04', Group, (False, False),   { 'rg' : (None, None)} ),
        ('05', Group, (False, False),
                { 'rg' : (0x100, None), 'sub' : (2, None)} ),
    ]

    for it in test.run(prog): yield it

def test_map_is_change():
    test = Expect(Walk(rings = [one, two, three]), should_isect_change)

    prog = [
        ('01', Change, (True, True, 2),    { 'rg' : (None, None)} ),
        ('02', Change, (True, False, 2),   { 'rg' : (None, None)} ),
        ('03', Change, (False, True, 2),  { 'rg' : (None, None)} ),
        ('04', Change, (False, False, 2),   { 'rg' : (None, None)} ),
    ]

    for it in test.run(prog): yield it

def test_map_is_group():
    test = Expect(Walk(rings = [one, two, three]), should_isect_group)

    prog = [
        ('01', Group, (True, True, 2),    { 'rg' : (None, None)} ),
        ('02', Group, (True, False, 2),   { 'rg' : (None, None)} ),
        ('03', Group, (False, True, 2),  { 'rg' : (None, None)} ),
        ('04', Group, (False, False, 2),   { 'rg' : (None, None)} ),
    ]

    for it in test.run(prog): yield it

def cook_diff2():
    diff = Diff(one = [one, two, three], two = [four])

    for place, left, right in diff(rg = (None, None), empty = True):
        print Tools.str(place), left, right


if __name__ == '__main__':
    cook_diff2()
