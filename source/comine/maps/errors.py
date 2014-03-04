#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.tools  import Tools

class MapError(Exception):
    pass

class MapOfSync(MapError):
    pass

class MapOutOf(MapError):
    def __init__(s, entity = None, rg = None):
        s.entity    = entity
        s.rg        = rg

        msg = 'rg %s is out of %s' % (Tools.str(rg), entity)

        MapError.__init__(s, msg)

class MapConflict(MapError):
    def __init__(s): pass
