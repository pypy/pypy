"""


"""
from pypy.interpreter.gateway import interp2app 
from pypy.interpreter.baseobjspace import Wrappable

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
        return space.unwrap(w_property).fget(space, w_obj)

    typedef = TypeDef("GetSetProperty",
        __get__ = interp2app(descr_property_get),
        )

def attrproperty(name):
    def fget(space, w_obj):
        obj = space.unwrap(w_obj)
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget)

def attrproperty_w(name):
    def fget(space, w_obj):
        obj = space.unwrap(w_obj)
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
from pypy.interpreter.function import Function, Method
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

Function.typedef = TypeDef("function",
    __call__ = interp2app(Function.descr_function_call.im_func),
    __get__ = interp2app(Function.descr_function_get.im_func),
    func_code = attrproperty('code'), 
    func_doc = attrproperty('doc'), 
    func_name = attrproperty('name'), 
    func_dict = attrproperty_w('w_func_dict'), 
    func_defaults = GetSetProperty(Function.fget_func_defaults),
    __doc__ = attrproperty('doc'), 
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

PyTraceback.typedef = TypeDef("traceback",
    tb_frame  = attrproperty('tb_frame'),
    tb_lasti  = attrproperty('tb_lasti'),
    tb_lineno = attrproperty('tb_line'),
    tb_next   = attrproperty('tb_next'),
    )

GeneratorIterator.typedef = TypeDef("generator",
    next       = interp2app(GeneratorIterator.descr_next.im_func),
    __iter__   = interp2app(GeneratorIterator.descr__iter__.im_func),
    gi_running = attrproperty('running'), 
    gi_frame   = attrproperty('frame'), 
)
