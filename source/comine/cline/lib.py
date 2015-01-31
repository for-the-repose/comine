#__ LGPL 3.0, 2015, Alexander Soloviev (no.friday@yandex.ru)

from gdb    import Command, COMMAND_OBSCURE, COMPLETE_NONE

from comine.cline.lang  import CFail, Parse
from comine.core.space  import Space


class CLines(Command):
    def __init__(s, space, invoke = lambda x, y, z: x(y, z)):
        Command.__init__(s, space, COMMAND_OBSCURE, COMPLETE_NONE, True)

        s.__base = '_%s__sub_%s_' % (s.__class__.__name__, space)
        s.__name    = space
        s.__invoke  = invoke
        s.__space   = Space()

    def invoke(s, args, tty):
        s.dont_repeat()

        argv = Parse(args)
        sub = argv.next()

        if sub is None:
            print('next level command expected')

        elif not s.__route(sub, argv):
            print('Unknown %s sub "%s"' % (s.__name, sub))

    def __route(s, sub, argv):
        cmd = getattr(s, s.__base + sub, None)

        if cmd is not None:
            infer = s.__space()

            try:
                s.__invoke(cmd, infer, argv)

            except CFail as E:
                print('-failed: %s' % E)

            except KeyboardInterrupt as E:
                print('-stopped by user')

            except Exception as E:
                raise

            return True

    @classmethod
    def register(cls, cline):
        cline()

        return cline
