#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

import gdb

class LibC(object):
    __slots__ = ('_LibC__tools', '_LibC__ready', '_LibC__types',
                    '_LibC__addr_t')

    def __init__(s, tools):
        assert tools.__gin__()

        s.__tools   = tools
        s.__ready   = False
        s.__types   = {}

        s.__disq_std_types()

        s.__addr_t = s.std_type('addr_t')

    def __ready__(s):       return s.__ready

    def std_type(s, name):  return s.__types.get(name)

    def addr(s, obj):       return long(obj.cast(s.__addr_t))

    def __disq_std_types(s):
        with s.__tools():
            s.__type_add('uintptr_t', alias = 'addr_t')
            s.__type_add('char', True, alias = 'ptr_t')
            s.__type_add('uint8_t', False, alias = 'byte')
            s.__type_add('size_t')

    def __type_add(s, name, ptr = False, alias = None):
        type_t = s.__type_lookup(name, ptr)

        if type_t is not None:
            s.__types[alias or name] = type_t

    def __type_lookup(s, name, ptr = False):
        try:
            type_t = gdb.lookup_type(name)

            return type_t.pointer() if ptr else type_t

        except:
            pass

