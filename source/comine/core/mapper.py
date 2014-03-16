#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from re     import match

import gdb

from comine.core.libc   import addr_t
from comine.core.logger import log
from comine.core.world  import World
from comine.core.base   import Core
from comine.misc.types  import Singleton
from comine.misc.humans import Humans


class Mapper(object):
    ''' Memory region mappings table registery '''

    __metaclass__ = Singleton

    MODE_CORE   = 1;    MODE_LIVE   = 2;    MODE_VOLATILE = 3

    __SYM_MODE = { MODE_CORE : 'core', MODE_LIVE : 'live',
                    MODE_VOLATILE : 'volatile' }

    def __init__(s):
        s.__mode        = None

        s.__infer   = gdb.selected_inferior()
        s.__world   = World()

        log(1, 'collecting memory in world...')

        s.__core    = Core(s)

        s.__discover_mode()

    def __world__(s):   return s.__world

    def search_memory(s, *kl, **kw):
        return s.__infer.search_memory(*kl, **kw)

    def register(s, *kl, **kw):
        s.__world.push(*kl, **kw)

    def validate(s, pointer, ro = False):
        addr = int(pointer)

        #__ amd64 ABI allows only 48 bit pointers
        if pointer >> 48: return False

        #__ lookup in the mappings table

        return True

    def __discover_mode(s):
        if len(s.__core) > 0:
            s.__mode = Mapper.MODE_CORE

        else:
            s.__mode = Mapper.MODE_LIVE

        log(1, 'mapper works in mode %s'
                    % (Mapper.__SYM_MODE.get(s.__mode),) )

    def readvar(s, var, size, gdbval = True, constructor = None):
        ''' Read blob from given memory location '''

        if gdbval is True:
            return var

        else:
            if isinstance(var, gdb.Value):
                var = int(var.cast(addr_t))

            blob = s.__infer.read_memory(var, size)

            return (constructor or (lambda x: x))(blob)

    @classmethod
    def varptr(cls, var, type_t = None):
        if type_t is None:
            type_t = var.type.pointer()

        return gdb.Value(var.address).cast(type_t)

