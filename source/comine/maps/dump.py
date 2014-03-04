#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.alias  import Alias

def dump(ring):
    print ring

    for span in ring:
        print '  ', span

        exten = span.exten()

        if isinstance(exten, Alias):
            for seq, alias in enumerate(exten):
                print '      alias #%u, 0x%x' % (seq, alias)
