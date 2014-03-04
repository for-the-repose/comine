
class Singleton(type):
    def __init__(cls, name, kl, kw):
        super(Singleton, cls).__init__(name, kl, kw)

        cls._instance = None

    def __call__(cls, *kl, **kw):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*kl, **kw)

        return cls._instance


class Types(object):
    @staticmethod
    def reset(s, attrs = None):
        if attrs is not None:
            raise Exception('Not implemented')

        else:
            for name in s.__class__.__slots__:
                setattr(s, name, None)

    @staticmethod
    def clone(s, exclude = tuple(), kw = None):
        cls, pref = s.__class__, s.__class__.__name__

        pref = ('' if pref[0] == '_' else '_') + pref + '__'

        off = len(pref)

        _filt = lambda x: x.startswith(pref) and x[off:] not in exclude

        _pair = lambda x: (x[off:], getattr(s, x))

        args = dict(map(_pair, filter(_filt, cls.__slots__)))

        if kw is not None: args.update(kw)

        return args

    @staticmethod
    def ensure(obj, types, none = False):
        if obj is None:
            if none is not True:
                raise TypeError('object is not set')

        elif types and not isinstance(obj, types):
            raise TypeError('Invalid type=%s' % obj)

        return obj
