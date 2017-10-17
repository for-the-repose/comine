#__ LGPL 3.0, 2015 Alexander Soloviev (no.friday@yandex.ru)

from comine.misc.func   import find
from comine.misc.humans import From

Items = From.items

Addr = lambda x: int(x, 0)

class CFail(Exception): pass

class Eval(object):
    def __init__(s, qry):
        s.__qry     = qry

    def __call__(s, args):
        state, kw, left = 1, {}, s.__forward(args)

        while state is not None:
            skip, case = s.__qry.get(state)

            rv = s.__handle(left, case)

            jump, act, val = s.__handle(left, case)

            state = skip if jump is False else jump

            if act:
                s.__action(kw, val, act)

            if state is None:
                return kw

            elif state == -1:
                raise CFail('unexpected token %s' % left)

            elif jump is not False:
                left = s.__forward(args)

    def __forward(s, args):
        if not args:
            raise CFail('one more token expected')

        else:
            return args.next()

    def __action(s, kw, val, act):
        val = val if len(act) == 1 else act[1]

        if isinstance(kw.get(act[0]), list):
            kw[act[0]].append(val)

        else:
            kw[act[0]] = val

    def __handle(s, left, case):
        rv = (False, None)

        if isinstance(case, list):
            sw = find(case, left, lambda x: x[0])

            rv = sw[1:] if sw else rv

        elif case is None:
            rv = (None if left is None else False, None)

        elif left is not None:
            rv = case[1:]

            try:
                left = case[0](left)

            except ValueError as E:
                raise CFail('%s' % str(E))

        return rv + (left,)


class Parse(object):
    def __init__(s, line):
        s.__line    = line + '\0'
        s.__off     = 0
        s.__on      = 0

    def __iter__(s):    return s

    def __nonzero__(s): return s.__off is not None

    def next(s):
        if s.__off is None:
            raise StopIteration()

        elif s.__off >= len(s.__line) - 1:
            s.__off = None

            return None

        else:
            for s.__off in xrange(s.__off, len(s.__line)):
                if not s.__line[s.__off].isspace(): break

            for z in xrange(s.__off, len(s.__line)):
                char = s.__line[z]

                if not (char.isalnum() or char in "_-+.:/"): break

            z = max(z, s.__off + 1)

            try:
                return s.__line[s.__off:z]

            finally:
                s.__off = z

