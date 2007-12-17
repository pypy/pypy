
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
    def __init__(self, space, w_selftype, w_starttype, w_type, w_self):
        self.w_selftype = w_selftype
        self.w_starttype = w_starttype
        self.w_type = w_type
        self.w_self = w_self

    def get(self, space, w_obj, w_type=None):
        w = space.wrap
        if self.w_self is None or space.is_w(w_obj, space.w_None):
            return w(self)
        else:
            return space.call_function(self.w_selftype, self.w_starttype, w_obj
                                       )
    get.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]

    def getattribute(self, space, name):
        w = space.wrap
        if name == '__class__':
            return self.w_selftype
        if self.w_type is None:
            return space.call_function(object_getattribute(space),
                                       w(self), w(name))
            
        w_value = space.lookup_in_type_starting_at(self.w_type,
                                                   self.w_starttype,
                                                   name)
        if w_value is None:
            return space.getattr(w(self), w(name))

        try:
            w_get = space.getattr(w_value, space.wrap('__get__'))
            if space.is_w(self.w_self, self.w_type):
                w_self = space.w_None
            else:
                w_self = self.w_self
        except OperationError, o:
            if not o.match(space, space.w_AttributeError):
                raise
            return w_value
        return space.call_function(w_get, w_self, self.w_type)
    getattribute.unwrap_spec = ['self', ObjSpace, str]

def descr_new_super(space, w_self, w_starttype, w_obj_or_type=None):
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
    return space.wrap(W_Super(space, w_self, w_starttype, w_type, w_obj_or_type))
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

    def new(space, w_type, w_fget=None, w_fset=None, w_fdel=None, w_doc=None):
        return W_Property(space, w_fget, w_fset, w_fdel, w_doc)
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
        if attr == '__doc__':
            return self.w_doc
        # shortcuts
        return space.call_function(object_getattribute(space),
                                   space.wrap(self), space.wrap(attr))
    getattribute.unwrap_spec = ['self', ObjSpace, str]

    def setattr(self, space, attr, w_value):
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

