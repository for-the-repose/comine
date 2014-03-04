#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

class IExten(object):
    "Span object extenstion interface"

    __slots__ = tuple()

    def __nonzero__(s): return True

    def __repr__(s):
        cname = s.__class__.__name__

        return '%s(%s)' % (cname, s.__desc__())

    def __desc__(s):        # -> str
        return '?'

    def __args__(s, rg):    # -> (*kl, **kw)
        '''
            Returns args required for constructing ranged subset copy
            of exten instnace at given place. Thus IExten(*kl, **kw)
            should be a valid invocation with properties:

                1. Original extension object should not be modified
                    while this call;

                2. Any futher mutation of cloned copy should not alter
                    original extension instance. However usage of CoW
                    approach and resource sharing are possible.
        '''

        raise Exception('Not implemented')

    def subset(s, rg):  # -> Exten | None
        kl, kw = s.__args__(rg)

        return s.__class__(*kl, **kw)

    def extend(s, rg, force = False):  # -> bool
        '''
            Check whether exten object may be keeped unchanged while
            parent Span() is being updated in its range - extended,
            narrowed or shifted.

            Exten should try do to all possible to complete extension
            if force arg is set to True, include any destructive ops.
        '''

        raise Exception('Not implemented')
