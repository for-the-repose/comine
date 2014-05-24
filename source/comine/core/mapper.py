#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

from re     import match

import gdb

from comine.core.libc   import LibC
from comine.core.logger import log
from comine.core.world  import World
from comine.core.base   import Core, Memory, Mappings
from comine.core.exun   import Exuns
from comine.misc.types  import Singleton
from comine.misc.humans import Humans
from comine.gdb.tools   import Tools

class Mapper(object):
    ''' Memory region mappings table registery '''

    __metaclass__ = Singleton

    MODE_CORE   = 1;    MODE_LIVE   = 2;    MODE_VOLATILE = 3

    __SYM_MODE = { MODE_CORE : 'core', MODE_LIVE : 'live',
                    MODE_VOLATILE : 'volatile' }

    def __init__(s):
        s.__mode        = None
        s.__gin         = gdb.selected_inferior()
        s.__tools       = Tools(gin = s.__gin)
        s.__world       = World()
        s.__attached    = False
        s.__world       = World()

        log(1, 'collecting memory in world...')

        s.__core    = Core(s)
        s.__memory  = None
        s.__exuns   = Exuns(s)
        s.__maps    = Mappings(s)

        s.__discover_mode()

        if s.__mode in (Mapper.MODE_LIVE, Mapper.MODE_VOLATILE):
            s.__maps.use_pid(s.__gin.pid)

            s.__memory = Memory(s)

        s.__libc    = LibC(s.__tools)
        s.__addr_t  = s.__libc.std_type('addr_t')

    def __world__(s):   return s.__world

    def __libc__(s):    return s.__libc

    def search_memory(s, *kl, **kw):
        return s.__gin.search_memory(*kl, **kw)

    def register(s, *kl, **kw):
        s.__world.push(*kl, **kw)

    def validate(s, pointer, ro = False):
        addr = int(pointer)

        #__ amd64 ABI allows only 48 bit pointers
        if pointer >> 48: return False

        #__ lookup in the mappings table

        return True

    def attach(s, path):
        s.__maps.use_file(path)

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
                var = int(var.cast(s.__addr_t))

            blob = s.__gin.read_memory(var, size)

            return (constructor or (lambda x: x))(blob)

    @classmethod
    def varptr(cls, var, type_t = None):
        if type_t is None:
            type_t = var.type.pointer()

        return gdb.Value(var.address).cast(type_t)

