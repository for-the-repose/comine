#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)


class IHeap(object):

    @classmethod
    def __who__(s):
        "Should provide name of heap impl"

        raise Exception('not impl')

    def __ready__(s):
        '''
            Should return heap status in following scheme
                True    -> discovered and ready;
                False   -> heap discover failed;
                None    -> not yet discovered, usually detected
                            by HeMan() instance holder;
        '''

        raise Exception('not impl')

    def look(s, at):
        raise Exception('not impl')

    def emum(s):
        raise Exception('not impl')
