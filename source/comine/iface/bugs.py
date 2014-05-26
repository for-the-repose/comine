#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class IBug(object):
    def __ver__(s):
        '''
            Gives runtime name and version range for which bug
            is applicable:

                -> name, (start, end)

            start and end version notation has form of:

                ver := (major, minor, release)
        '''

        raise Exception('not implemented')

    def __short__(s):
        ''' One line, up to 40-50 chars, bug description '''

        raise Exception('not implemented')

    def __str__(s):
        short = s.__short__()

        return short

    @classmethod
    def vlit(cls, ver, left = None):
        return '%u.%u.%u' % ver
