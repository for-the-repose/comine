from heap   import TheGlibcHeap
from maps   import MapRg
from math   import log as logE

def _bin(val):
    return int(logE(val) / logE(2.) + 1) if val > 0 else 0


class CMD_examp(gdb.Command):
    def __init__(s):
        gdb.Command.__init__(s, "example", gdb.COMMAND_OBSCURE)

    def invoke(s, args, tty):
        s.dont_repeat()

        heap = TheGlibcHeap()

        stats, total = [0] * 24, 0

        try:
            for chunk in heap.enum(used = True):
                size, blob = chunk.__blob__(gdbval=True)

                stats[_bin(size)] += 1
                total += size

        finally:
            print MapRg.human_bytes(total), stats


CMD_examp()

