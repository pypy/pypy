import weakref, operator
import py
from pypy.rpython.rarithmetic import r_uint
from pypy.tool.uid import Hashable
from pypy.tool.tls import tlsobject
from types import NoneType
from pypy.rpython.lltypesystem.lltype import LowLevelType, Signed, Unsigned, Float, Char
from pypy.rpython.lltypesystem.lltype import Bool, Void, UniChar, typeOf, Primitive
from pypy.rpython.lltypesystem.lltype import frozendict

class OOType(LowLevelType):
    pass

class Class(OOType):
    pass
Class = Class()

class Instance(OOType):
    """this is the type of user-defined objects"""
    def __init__(self, name, superclass, fields={}, methods={}):
        self._name = name
        self._superclass = superclass

        self._methods = frozendict()
        self._fields = frozendict()

        self._add_fields(fields)
        self._add_methods(methods)

        self._null = _null_instance(self)
        self._class = _class(self)
        
    def _defl(self):
        return self._null

    def _example(self):
        return new(self)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._name)

    def _add_fields(self, fields):
        fields = fields.copy()    # mutated below
        for name, defn in fields.iteritems():
            if self._lookup(name) is not None:
                raise TypeError("Cannot add field %r: method already exists" % name)
        
            if self._superclass is not None:
                if self._superclass._has_field(name):
                    raise TypeError("Field %r exists in superclass" % name)

            if type(defn) is not tuple:
                if isinstance(defn, Meth):
                    raise TypeError("Attempting to store method in field")
                
                fields[name] = (defn, defn._defl())
            else:
                ootype, default = defn

                if isinstance(ootype, Meth):
                    raise TypeError("Attempting to store method in field")

                if ootype != typeOf(default):
                    raise TypeError("Expected type %r for default" % (ootype,))

        self._fields.update(fields)

    def _add_methods(self, methods):
        # Note to the unwary: _add_methods adds *methods* whereas
        # _add_fields adds *descriptions* of fields.  This is obvious
        # if you are in the right state of mind (swiss?), but
        # certainly not necessarily if not.
        for name, method in methods.iteritems():
            if self._has_field(name):
                raise TypeError("Can't add method %r: field already exists" % name)
            if not isinstance(typeOf(method), Meth):
                raise TypeError("added methods must be _meths, not %s" % type(defn))
        self._methods.update(methods)

    def _init_instance(self, instance):
        if self._superclass is not None:
            self._superclass._init_instance(instance)
        
        for name, (ootype, default) in self._fields.iteritems():
            instance.__dict__[name] = default

    def _has_field(self, name):
        try:
            self._fields[name]
            return True
        except KeyError:
            if self._superclass is None:
                return False

            return self._superclass._has_field(name)

    def _field_type(self, name):
        try:
            return self._fields[name][0]
        except KeyError:
            if self._superclass is None:
                raise TypeError("No field names %r" % name)

            return self._superclass._field_type(name)

    _check_field = _field_type

    def _lookup(self, meth_name):
        meth = self._methods.get(meth_name)

        if meth is None and self._superclass is not None:
            meth = self._superclass._lookup(meth_name)

        return meth

    def _allfields(self):
        if self._superclass is None:
            all = {}
        else:
            all = self._superclass._allfields()
        all.update(self._fields)
        return all

class StaticMethod(OOType):

    def __init__(self, args, result):
        self.ARGS = tuple(args)
        self.RESULT = result

    def _example(self):
        _retval = self.RESULT._example()
        return _static_meth(self, _callable=lambda *args: _retval)
    
class Meth(StaticMethod):

    def __init__(self, args, result):
        StaticMethod.__init__(self, args, result)
# ____________________________________________________________

class _class(object):
    _TYPE = Class
    def __init__(self, INSTANCE):
        self._INSTANCE = INSTANCE
        
class _instance(object):
    
    def __init__(self, INSTANCE):
        self.__dict__["_TYPE"] = INSTANCE
        INSTANCE._init_instance(self)
        
    def __getattr__(self, name):
        meth = self._TYPE._lookup(name)
        if meth is not None:
            return meth._bound(self)
        
        self._TYPE._check_field(name)

        return self.__dict__[name]

    def __setattr__(self, name, value):
        self.__getattr__(name)
            
        if self._TYPE._field_type(name) != typeOf(value):
            raise TypeError("Expected type %r" % self._TYPE._field_type(name))

        self.__dict__[name] = value

    def __nonzero__(self):
        return True    # better be explicit -- overridden in _null_instance

    def __eq__(self, other):
        if not isinstance(other, _instance):
            raise TypeError("comparing an _instance with %r" % (other,))
        return self is other   # same comment as __nonzero__

    def __ne__(self, other):
        return not (self == other)

class _null_instance(_instance):

    def __init__(self, INSTANCE):
        self.__dict__["_TYPE"] = INSTANCE

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
    
        self._TYPE._check_field(name)
        
        raise RuntimeError("Access to field in null object")

    def __setattr__(self, name, value):
        _instance.__setattr__(self, name, value)

        raise RuntimeError("Assignment to field in null object")

    def __nonzero__(self):
        return False

    def __eq__(self, other):
        if not isinstance(other, _instance):
            raise TypeError("comparing an _instance with %r" % (other,))
        return not other

class _callable(object):

   def __init__(self, TYPE, **attrs):
       self._TYPE = TYPE
       self._name = "?"
       self._callable = None
       self.__dict__.update(attrs)

   def _checkargs(self, args):
       if len(args) != len(self._TYPE.ARGS):
           raise TypeError,"calling %r with wrong argument number: %r" % (self._TYPE, args)

       for a, ARG in zip(args, self._TYPE.ARGS):
           if not isCompatibleType(typeOf(a), ARG):
               raise TypeError,"calling %r with wrong argument types: %r" % (self._TYPE, args)
       callb = self._callable
       if callb is None:
           raise RuntimeError,"calling undefined function"
       return callb

class _static_meth(_callable):

   def __init__(self, STATICMETHOD, **attrs):
       assert isinstance(STATICMETHOD, StaticMethod)
       _callable.__init__(self, STATICMETHOD, **attrs)

   def __call__(self, *args):
       return self._checkargs(args)(*args)

class _meth(_callable):
   
    def __init__(self, METHOD, **attrs):
        assert isinstance(METHOD, Meth)
        _callable.__init__(self, METHOD, **attrs)

    def _bound(self, inst):
        return _bound_meth(inst, self)

class _bound_meth(object):
    def __init__(self, inst, meth):
        self.inst = inst
        self.meth = meth

    def __call__(self, *args):
        return self.meth._checkargs(args)(self.inst, *args)

def new(INSTANCE):
    return _instance(INSTANCE)

def runtimenew(class_):
    assert isinstance(class_, _class)
    return _instance(class_._INSTANCE)

def static_meth(FUNCTION, name,  **attrs):
    return _static_meth(FUNCTION, _name=name, **attrs)

def meth(METHOD, **attrs):
    return _meth(METHOD, **attrs)

def null(INSTANCE):
    return INSTANCE._null

def instanceof(inst, INSTANCE):
    # this version of instanceof() accepts a NULL instance and always
    # returns False in this case.
    assert isinstance(inst, _instance)
    assert isinstance(INSTANCE, Instance)
    return bool(inst) and isSubclass(inst._TYPE, INSTANCE)

def classof(inst):
    return runtimeClass(inst._TYPE)

def addFields(INSTANCE, fields):
    INSTANCE._add_fields(fields)

def addMethods(INSTANCE, methods):
    INSTANCE._add_methods(methods)

def runtimeClass(INSTANCE):
    assert isinstance(INSTANCE, Instance)
    return INSTANCE._class

def isSubclass(C1, C2):
    c = C1
    while c is not None:
        if c is C2:
            return True
        c = c._superclass
    return False

def commonBaseclass(INSTANCE1, INSTANCE2):
    c = INSTANCE1
    while c is not None:
        if isSubclass(INSTANCE2, c):
            return c
        c = c._superclass
    return None

def isCompatibleType(TYPE1, TYPE2):
    if TYPE1 == TYPE2:
        return True
    if isinstance(TYPE1, Instance) and isinstance(TYPE2, Instance):
        return isSubclass(TYPE1, TYPE2)
    else:
        return False
        
def ooupcast(INSTANCE, instance):
    assert instanceof(instance, INSTANCE)
    return instance
    
def oodowncast(INSTANCE, instance):
    assert instanceof(instance, INSTANCE)
    return instance
    
