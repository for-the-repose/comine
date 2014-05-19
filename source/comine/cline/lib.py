#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from gdb    import Command, COMMAND_OBSCURE, COMPLETE_NONE

from comine.core.mapper import Mapper


class CLines(Command):
    def __init__(s, space, invoke = lambda x, y, z: x(y, z)):
        Command.__init__(s, space, COMMAND_OBSCURE, COMPLETE_NONE, True)

        s.__base = '_%s__sub_%s_' % (s.__class__.__name__, space)
        s.__invoke = invoke

    def invoke(s, args, tty):
        s.dont_repeat()

        argv = args.split()

        sub, argv = argv[0], (argv[1:] if len(argv) > 1 else [])

        if not s.__route(sub, argv):
            raise Exception('unknown command %s' % sub)

    def __route(s, sub, argv):
        cmd = getattr(s, s.__base + sub, None)

        if cmd is not None:
            infer = Mapper()

            try:
                s.__invoke(cmd, infer, argv)

            except Exception as E:
                raise

            else:
                return True

    @classmethod
    def register(cls, cline):
        cline()

        return cline
