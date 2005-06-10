import autopath

import sets

debug = False

def create_property(cls, la, name):
    def get(self):
        self.setup()
        if la not in self.__dict__:
            raise AttributeError, ("'%s' object has no attribute '%s'" %
                                   (name, la))
        return self.__dict__[la]

    def set(self, value):
        self.__dict__[la] = value

    def del_(self):
        if la not in self.__dict__:
            raise AttributeError, ("'%s' object has no attribute '%s'" %
                                   (name, la))
        del self.__dict__[la]
    setattr(cls, la, property(get, set, del_))

class MetaLazyRepr(type):
    def __init__(cls, name, bases, dct):
        if "lazy_attributes" in dct:
            csetup = cls.setup
            def setup(self):
                if self.__setup_called__:
                    return
                if debug:
                    print "calling setup of class", name
                self.__setup_called__ = True
                self.gen.lazy_objects.discard(self)
                ret = csetup(self)
                return ret
            cls.setup = setup
            c__init__ = cls.__init__
            def __init__(self, *args, **kwds):
                c__init__(self, *args, **kwds)
                self.gen.lazy_objects.add(self)
                self.__setup_called__ = False
            cls.__init__ = __init__
            for la in dct["lazy_attributes"]:
                create_property(cls, la, name)
        super(MetaLazyRepr, cls).__init__(name, bases, dct)

