#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class LayoutError(Exception):
    pass

class ILayout(object):
    def __binary__(s):
        ''' Path to binary executable '''

        raise Exception('not implemented')

    def __core__(s):
        ''' Path to core image file '''

        raise Exception('not implemented')

    def __maps__(s):
        '''
            Optional copy of /proc/${pid}/maps file made just before
            core generation, or while this process.
        '''

        return None

    def __root__(s):
        '''
            Optional path to prepared root directory with actual
            shared objects linked with binaty and its debug symbols.
        '''

        return None
