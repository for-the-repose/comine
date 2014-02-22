#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class _MapEntity(object):
    def __init__(s):
        s.__sections = []

    def push(s, section, rg):
        s.__sections.append((rg, section))


class Binary(_MapEntity):
    ''' Binary executable object '''

    def __init__(s):
        _MapEntity.__init__(s)

    def __str__(s): return '<_Binary object>'

    def __repr__(s): return s.__str__()


class DSO(_MapEntity):
    ''' Dynamic shared object '''

    def __init__(s, name):
        _MapEntity.__init__(s)

        s.__name = name.strip()

    def __str__(s): return '<_DSO at %s>' % s.__name

    def __repr__(s): return s.__str__()

    def __name__(s): return s.__name
