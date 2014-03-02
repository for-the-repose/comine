
class Singleton(type):
    def __init__(cls, name, kl, kw):
        super(Singleton, cls).__init__(name, kl, kw)

        cls._instance = None

    def __call__(cls, *kl, **kw):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*kl, **kw)

        return cls._instance
