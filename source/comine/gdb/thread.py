#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from re     import match


class Threads(object):
    def __init__(s, tool):
        s.__tool    = tool

    def enum(s):
        lines = s.__tool.call('info threads')

        def _take(line):
            g = match('(\*)?\s*(\d+)\s+', line.strip())

            if g is not None:
                return (g.group(1) is not None, int(g.group(2)))

        thr = filter(None, map(_take, lines.split('\n')))

        defl = filter(lambda x: x[0], thr)[0][1]

        try:
            for used, no in thr:
                s.__tool.call('thread %u' % no)

                yield no, s.register('rsp')

        finally:
            s.__tool.call('thread %u' % defl)


    def register(s, reg):
        line = s.__tool.call('printf "0x%%llx", $%s' % reg)

        return int(line, 16)
