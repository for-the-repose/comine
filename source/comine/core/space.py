#__ LGPL 3.0, 2013 Alexander Soloviev (no.friday@yandex.ru)

import gdb

from comine.iface.infer import ILayout
from comine.misc.types  import Singleton
from comine.core.infer  import Infer
from comine.core.plugs  import Plugs
from comine.gdb.tools   import Tools

class Space(object):
    __metaclass__ = Singleton

    __slots__ = ('_Space__inmap', '_Space__tools', '_Space__plugs')

    def __init__(s):
        s.__inmap   = {} # { gin -> Infer() }
        s.__tools   = Tools()
        s.__plugs   = Plugs()

    def __call__(s):
        empty, gin = s.__gin_selected()

        if not empty:
            return s.__inmap.get(gin)

    def info(s):
        return s.__tools.version()

    def boot(s, fresh = False):
        s.__plugs.load(force = fresh)

    def open(s, source = None):
        gin = s.__gin_for(source)

        if gin is None:
            raise Exception('Cannot locate inferior for %s' % source)

        if gin in s.__inmap:
            raise Exception('Already attached inferior')

        tools = Tools(gin)

        s.__plugs.load()
        s.__prepare(tools, source)

        s.__inmap[gin] = Infer(tools, source)

    def __prepare(s, tools, source):
        if isinstance(source, ILayout):
            tools.load(source)

        elif isinstance(source, int):
            tools.attach(source)

    def __gin_for(s, source):
        if isinstance(source, (ILayout, int)):
            return s.__gin_create()

        elif source is None:
            empty, gin = s.__gin_selected()

            if not empty:
                return gin

        else:
            raise Exception('unknown source tyoe=%s' % source)

    def __gin_create(s):
        empty, gin = s.__gin_selected()

        return gin if empty else s.__tools.make()

    def __gin_selected(s):
        infer = s.__tools.__sel__()

        empty = not infer.is_valid() or infer.pid < 1

        return (empty, infer)
