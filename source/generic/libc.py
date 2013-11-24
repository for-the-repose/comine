#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

import gdb


def ptrtype(name):
    try:
        t = gdb.lookup_type(name)
        
        return t.pointer()

    except:
        return None
        

try:
    addr_t  = gdb.lookup_type('uintptr_t')
    ptr_t   = gdb.lookup_type('char').pointer()
    pptr_t  = ptr_t.pointer()
    size_t  = gdb.lookup_type('size_t')
    char_t  = gdb.lookup_type('char').pointer()
    psize_t = size_t.pointer()

except gdb.error as E:
    print 'Seems there is no debug symbols for GLibC library'

    raise

