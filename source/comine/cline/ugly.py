#__ LGPL 3.0, 2017, Alexander Soloviev (no.friday@yandex.ru)

from gdb    import Command, COMMAND_USER, COMPLETE_NONE

from comine.cline.lib   import CLines

@CLines.register
class CUgly(Command):
    def __init__(s):
        Command.__init__(s, 'ugly', COMMAND_USER, COMPLETE_NONE, True)
