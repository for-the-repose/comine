#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from re     import match
from gdb    import execute

from comine.iface.maps  import IMaps

class Targets(object):
    @classmethod
    def enum(cls):
        back = None

        lines = execute('info target', to_string = True)

        for line in lines.split('\n'):
            line = line.strip()

            g = match('(0x[\da-f]+) - (0x[\da-f]+) is (.*)', line)

            if g is not None:
                g = g.groups()

                rg = ((int(g[0], 16), int(g[1], 16)))

                if back == IMaps.BACK_EXUN:
                    m = match('(\.[\w._-]+)(?:\s+in\s+(.*))?', g[2])

                    if m is not None:
                        section = m.group(1).strip()
                        name = (m.group(2) or '').strip()

                        yield (back, rg, section, name)

                elif back == IMaps.BACK_CORE:
                    yield (back, rg, None, None)

            else:
                g = match('Local ([\w\s]+) file:', line)

                if g and g.group(1) == 'core dump':
                    back = IMaps.BACK_CORE

                elif g and g.group(1) == 'exec':
                    back = IMaps.BACK_EXUN
