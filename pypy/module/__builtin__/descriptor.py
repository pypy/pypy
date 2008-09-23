
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import object_getattribute
from pypy.interpreter.function import StaticMethod, ClassMethod
from pypy.interpreter.typedef import GetSetProperty, descr_get_dict, \
     descr_set_dict, interp_attrproperty_w

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
    get.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

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
    getattribute.unwrap_spec = ['self', ObjSpace, str]

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
descr_new_super.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root]

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
    def __init__(self, space, w_fget, w_fset, w_fdel, w_doc):
        self.w_fget = w_fget
        self.w_fset = w_fset
        self.w_fdel = w_fdel
        self.w_doc = w_doc

    def new(space, w_subtype, w_fget=None, w_fset=None, w_fdel=None, w_doc=None):
        w_result = space.allocate_instance(W_Property, w_subtype)
        W_Property.__init__(w_result, space, w_fget, w_fset, w_fdel, w_doc)
        return w_result
    new.unwrap_spec = [ObjSpace, W_Root, W_Root, W_Root, W_Root, W_Root]

    def get(self, space, w_obj, w_objtype=None):
        if space.is_w(w_obj, space.w_None):
            return space.wrap(self)
        if space.is_w(self.w_fget, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "unreadable attribute"))
        return space.call_function(self.w_fget, w_obj)
    get.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def set(self, space, w_obj, w_value):
        if space.is_w(self.w_fset, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "can't set attribute"))
        space.call_function(self.w_fset, w_obj, w_value)
        return space.w_None
    set.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def delete(self, space, w_obj):
        if space.is_w(self.w_fdel, space.w_None):
            raise OperationError(space.w_AttributeError, space.wrap(
                "can't delete attribute"))
        space.call_function(self.w_fdel, w_obj)
        return space.w_None
    delete.unwrap_spec = ['self', ObjSpace, W_Root]

    def getattribute(self, space, attr):
        # XXX fixme: this is a workaround.  It's hard but not impossible
        # to have both a __doc__ on the 'property' type, and a __doc__
        # descriptor that can read the docstring of 'property' instances.
        if attr == '__doc__':
            return self.w_doc
        # shortcuts
        return space.call_function(object_getattribute(space),
                                   space.wrap(self), space.wrap(attr))
    getattribute.unwrap_spec = ['self', ObjSpace, str]

    def setattr(self, space, attr, w_value):
        # XXX kill me?  This is mostly to make tests happy, raising
        # a TypeError instead of an AttributeError and using "readonly"
        # instead of "read-only" in the error message :-/
        raise OperationError(space.w_TypeError, space.wrap(
            "Trying to set readonly attribute %s on property" % (attr,)))
    setattr.unwrap_spec = ['self', ObjSpace, str, W_Root]

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
    __new__ = interp2app(W_Property.new.im_func),
    __get__ = interp2app(W_Property.get),
    __set__ = interp2app(W_Property.set),
    __delete__ = interp2app(W_Property.delete),
    __getattribute__ = interp2app(W_Property.getattribute),
    __setattr__ = interp2app(W_Property.setattr),
    fdel = interp_attrproperty_w('w_fdel', W_Property),
    fget = interp_attrproperty_w('w_fget', W_Property),
    fset = interp_attrproperty_w('w_fset', W_Property),
)

