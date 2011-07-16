from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import (TypeDef, interp_attrproperty_w,
    generic_new_descr)
from pypy.objspace.descroperation import object_getattribute

class W_Super(Wrappable):
    def __init__(self, space, w_starttype, w_objtype, w_self):
        self.w_starttype = w_starttype
        self.w_objtype = w_objtype
        self.w_self = w_self

    def get(self, space, w_obj, w_type=None):
        w = space.wrap
        if self.w_self is None or space.is_w(w_obj, space.w_None):
            return w(self)
        else:
            # if type(self) is W_Super:
            #     XXX write a fast path for this common case
            w_selftype = space.type(w(self))
            return space.call_function(w_selftype, self.w_starttype, w_obj)

    @unwrap_spec(name=str)
    def getattribute(self, space, name):
        w = space.wrap
        # only use a special logic for bound super objects and not for
        # getting the __class__ of the super object itself.
        if self.w_objtype is not None and name != '__class__':
            w_value = space.lookup_in_type_starting_at(self.w_objtype,
                                                       self.w_starttype,
                                                       name)
            if w_value is not None:
                w_get = space.lookup(w_value, '__get__')
                if w_get is None:
                    return w_value
                # Only pass 'obj' param if this is instance-mode super
                # (see CPython sourceforge id #743627)
                if self.w_self is self.w_objtype:
                    w_obj = space.w_None
                else:
                    w_obj = self.w_self
                return space.get_and_call_function(w_get, w_value,
                                                   w_obj, self.w_objtype)
        # fallback to object.__getattribute__()
        return space.call_function(object_getattribute(space),
                                   w(self), w(name))

def descr_new_super(space, w_subtype, w_starttype, w_obj_or_type=None):
    if space.is_w(w_obj_or_type, space.w_None):
        w_type = None  # unbound super object
    else:
        w_objtype = space.type(w_obj_or_type)
        if space.is_true(space.issubtype(w_objtype, space.w_type)) and \
            space.is_true(space.issubtype(w_obj_or_type, w_starttype)):
            w_type = w_obj_or_type # special case for class methods
        elif space.is_true(space.issubtype(w_objtype, w_starttype)):
            w_type = w_objtype # normal case
        else:
            try:
                w_type = space.getattr(w_obj_or_type, space.wrap('__class__'))
            except OperationError, o:
                if not o.match(space, space.w_AttributeError):
                    raise
                w_type = w_objtype
            if not space.is_true(space.issubtype(w_type, w_starttype)):
                raise OperationError(space.w_TypeError,
                    space.wrap("super(type, obj): "
                               "obj must be an instance or subtype of type"))
    # XXX the details of how allocate_instance() should be used are not
    # really well defined
    w_result = space.allocate_instance(W_Super, w_subtype)
    W_Super.__init__(w_result, space, w_starttype, w_type, w_obj_or_type)
    return w_result

W_Super.typedef = TypeDef(
    'super',
    __new__          = interp2app(descr_new_super),
    __getattribute__ = interp2app(W_Super.getattribute),
    __get__          = interp2app(W_Super.get),
    __doc__          =     """super(type) -> unbound super object
super(type, obj) -> bound super object; requires isinstance(obj, type)
super(type, type2) -> bound super object; requires issubclass(type2, type)

Typical use to call a cooperative superclass method:

class C(B):
    def meth(self, arg):
        super(C, self).meth(arg)"""
)

class W_Property(Wrappable):
    _immutable_fields_ = ["w_fget", "w_fset", "w_fdel"]

    def __init__(self, space):
        pass

    def init(self, space, w_fget=None, w_fset=None, w_fdel=None, w_doc=None):
        self.w_fget = w_fget
        self.w_fset = w_fset
        self.w_fdel = w_fdel
        self.w_doc = w_doc
        self.getter_doc = False
        # our __doc__ comes from the getter if we don't have an explicit one
        if (space.is_w(self.w_doc, space.w_None) and
            not space.is_w(self.w_fget, space.w_None)):
            w_getter_doc = space.findattr(self.w_fget, space.wrap("__doc__"))
            if w_getter_doc is not None:
                if type(self) is W_Property:
                    self.w_doc = w_getter_doc
                else:
                    space.setattr(space.wrap(self), space.wrap("__doc__"),
                                  w_getter_doc)
                self.getter_doc = True

    def get(self, space, w_obj, w_objtype=None):
        if space.is_w(w_obj, space.w_None):
            return space.wrap(self)
        if space.is_w(self.w_fget, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "unreadable attribute"))
        return space.call_function(self.w_fget, w_obj)

    def set(self, space, w_obj, w_value):
        if space.is_w(self.w_fset, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "can't set attribute"))
        space.call_function(self.w_fset, w_obj, w_value)
        return space.w_None

    def delete(self, space, w_obj):
        if space.is_w(self.w_fdel, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "can't delete attribute"))
        space.call_function(self.w_fdel, w_obj)
        return space.w_None

    def getter(self, space, w_getter):
        return self._copy(space, w_getter=w_getter)

    def setter(self, space, w_setter):
        return self._copy(space, w_setter=w_setter)

    def deleter(self, space, w_deleter):
        return self._copy(space, w_deleter=w_deleter)

    def _copy(self, space, w_getter=None, w_setter=None, w_deleter=None):
        if w_getter is None:
            w_getter = self.w_fget
        if w_setter is None:
            w_setter = self.w_fset
        if w_deleter is None:
            w_deleter = self.w_fdel
        if self.getter_doc and w_getter is not None:
            w_doc = space.w_None
        else:
            w_doc = self.w_doc
        w_type = self.getclass(space)
        return space.call_function(w_type, w_getter, w_setter, w_deleter, w_doc)

W_Property.typedef = TypeDef(
    'property',
    __doc__ = '''property(fget=None, fset=None, fdel=None, doc=None) -> property attribute

fget is a function to be used for getting an attribute value, and likewise
fset is a function for setting, and fdel a function for deleting, an
attribute.  Typical use is to define a managed attribute x:
class C(object):
    def getx(self): return self.__x
    def setx(self, value): self.__x = value
    def delx(self): del self.__x
    x = property(getx, setx, delx, "I am the 'x' property.")''',
    __new__ = generic_new_descr(W_Property),
    __init__ = interp2app(W_Property.init),
    __get__ = interp2app(W_Property.get),
    __set__ = interp2app(W_Property.set),
    __delete__ = interp2app(W_Property.delete),
    fdel = interp_attrproperty_w('w_fdel', W_Property),
    fget = interp_attrproperty_w('w_fget', W_Property),
    fset = interp_attrproperty_w('w_fset', W_Property),
    getter = interp2app(W_Property.getter),
    setter = interp2app(W_Property.setter),
    deleter = interp2app(W_Property.deleter),
)
# This allows there to be a __doc__ of the property type and a __doc__
# descriptor for the instances.
W_Property.typedef.rawdict['__doc__'] = interp_attrproperty_w('w_doc',
                                                              W_Property)

