#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.exten  import IExten
from comine.maps.tools  import Tools

class IOwner(object):
    "Rings owner iface definition"


class EPhys(IExten):
    '''
        Base span extension iface for physical memory backing
        (RAM, mapped binaries or any other addressable data) in
        world of rings API abstaction.
    '''

    __slots__ = tuple()

    def __rg__(s):
        '''
            Return bounded memory region that handled by this exten
        '''

        raise Exception('Not implemented')

    def search(s, sub, skip = True): # -> at
        '''
            Search supplied sub blob string inside physical region
            and yields addresses of its occurrence. If optional arg
            skip is set to True search must skip matched substring
            and go on just after its end.
        '''

        raise Exception('Not implemented')

    def dump(s, func, rg = None, blocks = 8192):
        '''
            Should invoke func(blob) sequentially for each block of
            span at most of size blocks falling in region rg. Finally
            should return number of passed bytes.
        '''

        rg = Tools.isect(s.__rg__(), rg or s.__rg__())

        at = rg[0]

        while at is not None and at < rg[1]:
            data = s.read(at, min(rg[1] - at, blocks))

            if len(data) < 1:
                raise Exception('Invalid phys read() impl')

            func(data)

            at += len(data)

        return at - rg[0]

    def read(s, at, blocks):
        ''' Single data read call '''

        raise Exception('Not implemented')
