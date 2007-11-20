"""
Plain Python definition of the builtin descriptors.
"""

# Descriptor code, shamelessly stolen from Raymond Hettinger:
#    http://users.rcn.com/python/download/Descriptor.htm


# XXX there is an interp-level pypy.interpreter.function.StaticMethod
# XXX because __new__ needs to be a StaticMethod early.
class staticmethod(object):
    """staticmethod(function) -> static method

Convert a function to be a static method.

A static method does not receive an implicit first argument.
To declare a static method, use this idiom:

     class C:
         def f(arg1, arg2, ...): ...
         f = staticmethod(f)

It can be called either on the class (e.g. C.f()) or on an instance
(e.g. C().f()).  The instance is ignored except for its class."""
    __slots__ = ['_f']

    def __init__(self, f):
        self._f = f

    def __get__(self, obj, objtype=None):
        return self._f


class classmethod(object):
    """classmethod(function) -> class method

Convert a function to be a class method.

A class method receives the class as implicit first argument,
just like an instance method receives the instance.
To declare a class method, use this idiom:

  class C:
      def f(cls, arg1, arg2, ...): ...
      f = classmethod(f)

It can be called either on the class (e.g. C.f()) or on an instance
(e.g. C().f()).  The instance is ignored except for its class.
If a class method is called for a derived class, the derived class
object is passed as the implied first argument."""
    __slots__ = ['_f']

    def __init__(self, f):
        if not callable(f):
            raise TypeError, "'%s' object is not callable" % type(f).__name__
        self._f = f

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return MethodType(self._f, klass)

def dummy(): pass
MethodType = type(dummy.__get__(42))
del dummy

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
