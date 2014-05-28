#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class AnalysisError(Exception):
    ''' Internal error of analytical core, must never happen '''

class ErrorDamaged(Exception):
    ''' Unexpected data found while analysis '''

    def __init__(s, msg):
        log(1, msg)

        Exception.__init__(s)

class ErrorChunk(ErrorDamaged):
    def __init__(s, chunk, msg):
        s.chunk     = chunk
        s.msg       = msg

    def __str__(s):
        return 'chunk at 0x%x: %s' % (s.chunk.__at__(), s.msg)
