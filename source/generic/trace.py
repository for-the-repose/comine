
from sys        import exc_info
from time       import gmtime, strftime
from traceback  import format_exc
from inspect    import getargvalues


def trace_write(_call, extended = False):
    _utc = strftime('%Y-%m-%d %H:%M:%S', gmtime())

    _call('** trace generated at ' + _utc + '\n\n')
    _call(format_exc())

    if extended is True:
        _call('\nExtended traceback expansoin\n')

        traceback = exc_info()[2]; depth = 0

        while traceback is not None:
            frame   = traceback.tb_frame
            code    = frame.f_code
            args    = getargvalues(frame)

            _call('% x: File "%s", line %i, in %s\n' %
                    ( depth,
                        code.co_filename,
                        traceback.tb_lineno,
                        code.co_name))

            _call('     --locals: ')

            try:
                _call(str(frame.f_locals) + '\n\n')

            except Exception as E:
                _call('exception='+str(E))

            traceback = traceback.tb_next; depth += 1
