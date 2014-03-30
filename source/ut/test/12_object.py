#!/usr/bin/env python2

from sys        import path
from os.path    import abspath, expanduser, dirname

_P_BASE     = abspath(expanduser(dirname(__file__)))
_P_ADD      = [ '/../', '/../../' ]

for x in _P_ADD: path.insert(0, _P_BASE + x)

from comine.maps.tools  import Tools
from comine.maps.span   import Span
from comine.maps.ring   import Ring
from comine.maps.dump   import dump
from comine.maps.walk   import Walk, Diff, OneBy
from comine.maps.aggr   import Change, Group, Align

from data.D10_rings		import *


class Check(object):
    def __init__(s, should):
        s.__should  = should

    def __call__(s, it):
        keys = set(s.__should.keys())

        for span, regs in it:
            check = s.__should.get(span)

            if check != regs:
                raise Exception('fail')

            keys.remove(span)

        if len(keys) > 0:
            raise Exception('not all keys covered')

    @classmethod
    def dump(cls, it):
        for span, regs in it:
            print span, '%x' % id(span)

            for place in regs:
                print '  ', Tools.str(place)


def test_map_object():
    check   = Check(should_isect_object)
    walk    = Walk(rings = [one, two, three])

    check(walk(Align(False, cuts = 2), rg = (None, None)))

def test_map_oneby_true():
    check   = Check(should_isect_oneby_true)
    walk    = OneBy(one = [one, two, three], two = [four])

    check(walk(rg = (None, None), mode = True))

def test_map_oneby_false():
    check   = Check(should_isect_oneby_false)
    walk    = OneBy(one = [one, two, three], two = [four])

    check(walk(rg = (None, None), mode = False))

if __name__ == '__main__':
    test_map_oneby_true()
