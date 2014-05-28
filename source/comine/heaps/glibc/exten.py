#__ LGPL 3.0, 2014 Alexander Soloviev (no.friday@yandex.ru)

from comine.maps.alias  import Alias

class EHeap(Alias):
    __slots__ = ('_EHeap__arena', '_EHeap__tag')

    TAG_BOUND   = 1 # Completely known full arena fragment
    TAG_FRAG    = 2 # Partially known part of arena fragment
    TAG_LEFT    = 3 # Left guessed continuation of fragment
    TAG_MMAPPED = 4 # mmap'ed guessed single allocation
    TAG_SINGLE  = 5 # isolated guessed arena fragment

    __NAMES = {
            TAG_BOUND:      'bound',
            TAG_FRAG:       'frag',
            TAG_LEFT:       'left',
            TAG_MMAPPED:    'mapped',
            TAG_SINGLE:     'single' }

    def __init__(s, arena = None, tag = None, *kl, **kw):
        Alias.__init__(s, *kl, **kw)

        s.__tag     = tag or EHeap.TAG_BOUND
        s.__arena   = arena

    def __tag__(s):     return s.__tag

    def __arena__(s):   return s.__arena

    def __desc__(s):
        tlit    = EHeap.__NAMES.get(s.__tag, '?%u' % s.__tag)
        alit    = '#%u' % s.__arena.__seq__() if s.__arena else '?'
        dlit    = Alias.__desc__(s)

        return 'arena %s, %s, %s' % (alit, tlit, dlit)

    def __args__(s, rg):
        kl, kw = Alias.__args__(s, rg)

        return ((s.__arena, s.__tag) + kl, kw)

    @classmethod
    def pred(cls, tag):
        return lambda span: span.exten().__tag__() == tag
