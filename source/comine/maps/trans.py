#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.errors import MapOfSync
from comine.maps.span   import Span

class Trans(object):
    '''Very simple transaction handler for Ring()'''

    __slots__ = ('_Trans__ring', '_Trans__pends', '_Trans__auto',
                    '_Trans__scn')

    def __init__(s, ring, auto = True):
        s.__ring    = ring
        s.__scn     = ring.__scn__()
        s.__pends   = []
        s.__auto    = auto

    def __enter__(s):   return s

    def __exit__(s, Et, Ev, tb):
        if Et is None and s.__auto is True:
            s.commit()

    def __len__(s):     return len(s.__pends)

    def commit(s):
        if s.__scn != s.__ring.__scn__():
            raise MapOfSync()

        for span in s.__pends:
            s.__ring.push(span)

        s.drop()

    def drop(s):
        s.__pends = []

    def make(s, *kl, **kw):
        span = Span(*kl, **kw)

        s.__pends.append(span)

        return span
