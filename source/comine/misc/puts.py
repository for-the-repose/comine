#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from os.path    import dirname, isdir, exists

class Puts(object):
    __slots__ = ('_Puts__base', '_Puts__file', '_Puts__seq',
                    '_Puts__written', '_Puts__label')

    def __init__(s, base, label = False):
        s.__base    = base
        s.__file    = None
        s.__seq     = -1
        s.__written = 0
        s.__label   = label

        direcoty = dirname(base)

        if not isdir(direcoty):
            raise Exception('does not exists=%s' % direcoty)

    def __ready__(s):   return s.__file is not None

    def __seq__(s):     return s.__seq

    def __stats__(s):   return (s.__seq  + 1, s.__written)

    def __call__(s, data):
        s.__file.write(data)

        s.__written += len(data)

    def __enter__(s):   return s

    def __exit__(s, Et, Ev, tb):
        s.close()

    def next(s, suffix):
        s.close()

        seqn    = s.__seq + 1
        middle  = ('_%02x' % seqn) if s.__label else ''
        path    = s.__base + middle + suffix

        if exists(path):
            raise Exception('already exists=%s' % path)

        s.__file    = open(path, 'wb')
        s.__seq     = seqn

    def close(s):
        if s.__ready__():
            s.__file.close()

            s.__file = None
