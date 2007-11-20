"""
Plain Python definition of the builtin descriptors.
"""

# Descriptor code, shamelessly stolen from Raymond Hettinger:
#    http://users.rcn.com/python/download/Descriptor.htm

# It's difficult to have a class that has both a docstring and a slot called
# '__doc__', but not impossible...
class docstring(object):

    def __init__(self, classdocstring):
        self.classdocstring = classdocstring
        self.slot = None

    def capture(cls, slotname):
        self = cls.__dict__['__doc__']
        slot = cls.__dict__[slotname]
        if not isinstance(self, docstring):
            raise TypeError, "the class __doc__ must be a docstring instance"
        self.slot = slot
        delattr(cls, slotname)
    capture = staticmethod(capture)

    def __get__(self, p, cls=None):
        if p is None:
            return self.classdocstring  # getting __doc__ on the class
        elif self.slot is None:
            raise AttributeError, "'%s' instance has no __doc__" % (
                p.__class__.__name__,)
        else:
            return self.slot.__get__(p) # getting __doc__ on an instance

    def __set__(self, p, value):
        if hasattr(self.slot, '__set__'):
            return self.slot.__set__(p, value)
        else:
            raise AttributeError, "cannot write __doc__"

    def __delete__(self, p):
        if hasattr(self.slot, '__delete__'):
            return self.slot.__delete__(p)
        else:
            raise AttributeError, "cannot write __doc__"


class property(object):
    __doc__ = docstring(
        '''property(fget=None, fset=None, fdel=None, doc=None) -> property attribute

fget is a function to be used for getting an attribute value, and likewise
fset is a function for setting, and fdel a function for deleting, an
attribute.  Typical use is to define a managed attribute x:
class C(object):
    def getx(self): return self.__x
    def setx(self, value): self.__x = value
    def delx(self): del self.__x
    x = property(getx, setx, delx, "I am the 'x' property.")''')

    __slots__ = ['fget', 'fset', 'fdel', 'slot__doc__']

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self         
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj)

docstring.capture(property, 'slot__doc__')
