"""


"""
from pypy.interpreter.gateway import interp2app 
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError

class TypeDef:
    def __init__(self, __name, **rawdict):
        self.name = __name
        self.rawdict = rawdict

    def mro(self, space):
        if self is space.object_typedef:
            return [self]
        else:
            return [self, space.object_typedef]

class GetSetProperty(Wrappable):
    def __init__(self, fget, fset=None, fdel=None, doc=None):
        fget = getattr(fget, 'im_func', fget) 
        fset = getattr(fset, 'im_func', fset) 
        fdel = getattr(fdel, 'im_func', fdel) 
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc

    def descr_property_get(space, w_property, w_obj, w_ignored):
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if w_obj == space.w_None and not space.is_true(space.is_(w_ignored, space.type(space.w_None))):
            #print w_property, w_obj, w_ignored
            return w_property
        else:
            return space.unwrap(w_property).fget(space, w_obj)

    def descr_property_set(space, w_property, w_obj, w_value):
        fset = space.unwrap(w_property).fset
        if fset is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("read-only attribute"))
        fset(space, w_obj, w_value)

    def descr_property_del(space, w_property, w_obj):
        fdel = space.unwrap(w_property).fdel
        if fdel is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("cannot delete attribute"))
        fdel(space, w_obj)

    typedef = TypeDef("GetSetProperty",
        __get__ = interp2app(descr_property_get),
        __set__ = interp2app(descr_property_set),
        __delete__ = interp2app(descr_property_del),
        )

def attrproperty(name):
    def fget(space, w_obj):
        obj = space.unwrap_builtin(w_obj)
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget)

def attrproperty_w(name):
    def fget(space, w_obj):
        obj = space.unwrap_builtin(w_obj)
        w_value = getattr(obj, name)
        if w_value is None:
            return space.w_None
        else:
            return w_value 

    return GetSetProperty(fget)

# ____________________________________________________________
#
# Definition of the type's descriptors for all the internal types

from pypy.interpreter.eval import Code, Frame
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, Method, StaticMethod
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator 

Code.typedef = TypeDef('internal-code',
    co_name = attrproperty('co_name'),
    # XXX compute more co_xxx from the methods in Code
    )

Frame.typedef = TypeDef('internal-frame',
    f_code = attrproperty('code'),
    f_locals = GetSetProperty(Frame.fget_getdictscope.im_func,
                              ), # , setdictscope), XXX
    f_globals = attrproperty_w('w_globals'),
    )

PyCode.typedef = TypeDef('code',
    co_argcount = attrproperty('co_argcount'),
    co_nlocals = attrproperty('co_nlocals'),
    co_stacksize = attrproperty('co_stacksize'),
    co_flags = attrproperty('co_flags'),
    co_code = attrproperty('co_code'),
    co_consts = attrproperty('co_consts'),
    co_names = attrproperty('co_names'),
    co_varnames = attrproperty('co_varnames'),
    co_freevars = attrproperty('co_freevars'),
    co_cellvars = attrproperty('co_cellvars'),
    co_filename = attrproperty('co_filename'),
    co_name = attrproperty('co_name'),
    co_firstlineno = attrproperty('co_firstlineno'),
    co_lnotab = attrproperty('co_lnotab'),
    )

PyFrame.typedef = TypeDef('frame',
    f_builtins = attrproperty_w('w_builtins'),
    **Frame.typedef.rawdict)

Module.typedef = TypeDef("module",
    __dict__ = attrproperty_w('w_dict'), 
    )

getset_func_doc = GetSetProperty(Function.fget_func_doc,
                                 Function.fset_func_doc,
                                 Function.fdel_func_doc)

Function.typedef = TypeDef("function",
    __call__ = interp2app(Function.descr_function_call.im_func),
    __get__ = interp2app(Function.descr_function_get.im_func),
    func_code = attrproperty('code'), 
    func_doc = getset_func_doc,
    func_name = attrproperty('name'), 
    func_dict = attrproperty_w('w_func_dict'), 
    func_defaults = GetSetProperty(Function.fget_func_defaults),
    func_globals = attrproperty_w('w_func_globals'),
    __doc__ = getset_func_doc,
    __name__ = attrproperty('name'), 
    __dict__ = attrproperty_w('w_func_dict'), 
    # XXX func_closure, etc.pp
    )

Method.typedef = TypeDef("method",
    __call__ = interp2app(Method.descr_method_call.im_func),
    im_func  = attrproperty_w('w_function'), 
    im_self  = attrproperty_w('w_instance'), 
    im_class = attrproperty_w('w_class'),
    # XXX getattribute/setattribute etc.pp 
    )

StaticMethod.typedef = TypeDef("staticmethod",
    __get__ = interp2app(StaticMethod.descr_staticmethod_get.im_func),
    # XXX getattribute etc.pp
    )

PyTraceback.typedef = TypeDef("traceback",
    tb_frame  = attrproperty('frame'),
    tb_lasti  = attrproperty('lasti'),
    tb_lineno = attrproperty('lineno'),
    tb_next   = attrproperty('next'),
    )

GeneratorIterator.typedef = TypeDef("generator",
    next       = interp2app(GeneratorIterator.descr_next.im_func),
    __iter__   = interp2app(GeneratorIterator.descr__iter__.im_func),
    gi_running = attrproperty('running'), 
    gi_frame   = attrproperty('frame'), 
)
