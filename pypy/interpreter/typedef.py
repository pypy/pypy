"""


"""
from pypy.interpreter.gateway import interp2app 
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.tool.cache import Cache
import new

class TypeDef:
    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only"
        self.name = __name
        self.base = __base
        self.hasdict = '__dict__' in rawdict or (__base and __base.hasdict)
        self.rawdict = rawdict


unique_interplevel_subclass_cache = Cache()
def get_unique_interplevel_subclass(cls):
    return unique_interplevel_subclass_cache.getorbuild(cls, _buildusercls, None)

def _buildusercls(cls, ignored):
    "NOT_RPYTHON: initialization-time only"
    typedef = cls.typedef
    name = 'User' + cls.__name__
    body = {}

    class User_InsertNameHere(object):

        def getclass(self, space):
            return self.w__class__

        def setclass(self, w_subtype):
            # XXX sanity checks here
            self.w__class__ = w_subtype

        if typedef.hasdict:
            def user_setup(self, space, w_subtype):
                self.space = space
                self.w__class__ = w_subtype

        else:
            def getdict(self):
                return self.w__dict__

            def setdict(self, w_dict):
                space = self.space
                if not space.is_true(space.isinstance(w_dict, space.w_dict)):
                    raise OperationError(space.w_TypeError,
                            space.wrap("setting dictionary to a non-dict"))
                self.w__dict__ = w_dict

            def user_setup(self, space, w_subtype):
                self.space = space
                self.w__class__ = w_subtype
                self.w__dict__ = space.newdict([])

    body = dict([(key, value)
                 for key, value in User_InsertNameHere.__dict__.items()
                 if not key.startswith('_')])
    subcls = type(name, (cls,), body)
    return subcls

def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return object.__new__(cls)
    else:
        return new.instance(cls)

class GetSetProperty(Wrappable):
    def __init__(self, fget, fset=None, fdel=None, doc=None):
        "NOT_RPYTHON: initialization-time only"
        fget = getattr(fget, 'im_func', fget) 
        fset = getattr(fset, 'im_func', fset) 
        fdel = getattr(fdel, 'im_func', fdel) 
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc

    def descr_property_get(space, w_property, w_obj, w_cls=None):
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if w_obj == space.w_None and not space.is_true(space.is_(w_cls, space.type(space.w_None))):
            #print w_property, w_obj, w_cls
            return w_property
        else:
            return space.interpclass_w(w_property).fget(space, w_obj)

    def descr_property_set(space, w_property, w_obj, w_value):
        fset = space.interpclass_w(w_property).fset
        if fset is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("read-only attribute"))
        fset(space, w_obj, w_value)

    def descr_property_del(space, w_property, w_obj):
        fdel = space.interpclass_w(w_property).fdel
        if fdel is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("cannot delete attribute"))
        fdel(space, w_obj)

    typedef = TypeDef("GetSetProperty",
        __get__ = interp2app(descr_property_get),
        __set__ = interp2app(descr_property_set),
        __delete__ = interp2app(descr_property_del),
        )

def interp_attrproperty(name):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, w_obj):
        obj = space.interpclass_w(w_obj)
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget)

def interp_attrproperty_w(name):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, w_obj):
        obj = space.interpclass_w(w_obj)
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
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame, ControlFlowException
from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, Method, StaticMethod
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator 
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.special import NotImplemented, Ellipsis

def descr_get_dict(space, w_obj):
    obj = space.interpclass_w(w_obj)
    w_dict = obj.getdict()
    assert w_dict is not None, repr(obj)
    return w_dict

def descr_set_dict(space, w_obj, w_dict):
    obj = space.interpclass_w(w_obj)
    obj.setdict(w_dict)

interp_dict_descr = GetSetProperty(descr_get_dict, descr_set_dict)


# co_xxx interface emulation for built-in code objects
def fget_co_varnames(space, w_code):
    code = space.interpclass_w(w_code)
    return space.newtuple([space.wrap(name) for name in code.getvarnames()])

def fget_co_argcount(space, w_code):
    code = space.interpclass_w(w_code)
    argnames, varargname, kwargname = code.signature()
    return space.wrap(len(argnames))

def fget_co_flags(space, w_code):
    code = space.interpclass_w(w_code)
    argnames, varargname, kwargname = code.signature()
    flags = 0
    if varargname is not None: flags |= CO_VARARGS
    if kwargname  is not None: flags |= CO_VARKEYWORDS
    return space.wrap(flags)

def fget_co_consts(space, w_code):
    code = space.interpclass_w(w_code)
    w_docstring = space.wrap(code.getdocstring())
    return space.newtuple([w_docstring])

Code.typedef = TypeDef('internal-code',
    co_name = interp_attrproperty('co_name'),
    co_varnames = GetSetProperty(fget_co_varnames),
    co_argcount = GetSetProperty(fget_co_argcount),
    co_flags = GetSetProperty(fget_co_flags),
    co_consts = GetSetProperty(fget_co_consts),
    )

Frame.typedef = TypeDef('internal-frame',
    f_code = interp_attrproperty('code'),
    f_locals = GetSetProperty(Frame.fget_getdictscope.im_func),
    f_globals = interp_attrproperty_w('w_globals'),
    )

PyCode.typedef = TypeDef('code',
    __new__ = interp2app(PyCode.descr_code__new__.im_func),
    co_argcount = interp_attrproperty('co_argcount'),
    co_nlocals = interp_attrproperty('co_nlocals'),
    co_stacksize = interp_attrproperty('co_stacksize'),
    co_flags = interp_attrproperty('co_flags'),
    co_code = interp_attrproperty('co_code'),
    co_consts = GetSetProperty(PyCode.fget_co_consts),
    co_names = GetSetProperty(PyCode.fget_co_names),
    co_varnames = interp_attrproperty('co_varnames'),
    co_freevars = interp_attrproperty('co_freevars'),
    co_cellvars = interp_attrproperty('co_cellvars'),
    co_filename = interp_attrproperty('co_filename'),
    co_name = interp_attrproperty('co_name'),
    co_firstlineno = interp_attrproperty('co_firstlineno'),
    co_lnotab = interp_attrproperty('co_lnotab'),
    )

PyFrame.typedef = TypeDef('frame',
    f_builtins = interp_attrproperty_w('w_builtins'),
    f_lineno = GetSetProperty(PyFrame.fget_f_lineno.im_func),
    **Frame.typedef.rawdict)

Module.typedef = TypeDef("module",
    __new__ = interp2app(Module.descr_module__new__.im_func),
    __init__ = interp2app(Module.descr_module__init__.im_func),
    __dict__ = GetSetProperty(descr_get_dict), # module dictionaries are readonly attributes
    __getattr__ = interp2app(Module.descr_module__getattr__.im_func),
    )

getset_func_doc = GetSetProperty(Function.fget_func_doc,
                                 Function.fset_func_doc,
                                 Function.fdel_func_doc)

# __module__ attribute lazily gets its value from the w_globals
# at the time of first invocation. This is not 100% compatible but
# avoid problems at the time we construct the first functions when
# it's not really possible to do a get or getitem on dictionaries
# (mostly because wrapped exceptions don't exist at that time)
getset___module__ = GetSetProperty(Function.fget___module__,
                                   Function.fset___module__,
                                   Function.fdel___module__)

getset_func_defaults = GetSetProperty(Function.fget_func_defaults,
                                      Function.fset_func_defaults,
                                      Function.fdel_func_defaults)
getset_func_code = GetSetProperty(Function.fget_func_code,
                                  Function.fset_func_code)

getset_func_dict = GetSetProperty(descr_get_dict, descr_set_dict)

Function.typedef = TypeDef("function",
    __call__ = interp2app(Function.descr_function_call.im_func),
    __get__ = interp2app(Function.descr_function_get.im_func),
    func_code = getset_func_code, 
    func_doc = getset_func_doc,
    func_name = interp_attrproperty('name'), 
    func_dict = getset_func_dict, 
    func_defaults = getset_func_defaults,
    func_globals = interp_attrproperty_w('w_func_globals'),
    func_closure = GetSetProperty( Function.fget_func_closure ),
    __doc__ = getset_func_doc,
    __name__ = interp_attrproperty('name'),
    __dict__ = getset_func_dict,
    __module__ = getset___module__,
    # XXX func_closure, etc.pp
    )

Method.typedef = TypeDef("method",
    __new__ = interp2app(Method.descr_method__new__.im_func),
    __call__ = interp2app(Method.descr_method_call.im_func),
    __get__ = interp2app(Method.descr_method_get.im_func),
    im_func  = interp_attrproperty_w('w_function'), 
    im_self  = interp_attrproperty_w('w_instance'), 
    im_class = interp_attrproperty_w('w_class'),
    __getattribute__ = interp2app(Method.descr_method_getattribute.im_func),
    # XXX getattribute/setattribute etc.pp 
    )

StaticMethod.typedef = TypeDef("staticmethod",
    __get__ = interp2app(StaticMethod.descr_staticmethod_get.im_func),
    # XXX getattribute etc.pp
    )

PyTraceback.typedef = TypeDef("traceback",
    tb_frame  = interp_attrproperty('frame'),
    tb_lasti  = interp_attrproperty('lasti'),
    tb_lineno = interp_attrproperty('lineno'),
    tb_next   = interp_attrproperty('next'),
    )

GeneratorIterator.typedef = TypeDef("generator",
    next       = interp2app(GeneratorIterator.descr_next.im_func),
    __iter__   = interp2app(GeneratorIterator.descr__iter__.im_func),
    gi_running = interp_attrproperty('running'), 
    gi_frame   = interp_attrproperty('frame'), 
)

Cell.typedef = TypeDef("cell")

Ellipsis.typedef = TypeDef("Ellipsis", 
    __repr__   = interp2app(Ellipsis.descr__repr__.im_func),
)

NotImplemented.typedef = TypeDef("NotImplemented", 
    __repr__   = interp2app(NotImplemented.descr__repr__.im_func), 
)

ControlFlowException.typedef = TypeDef("ControlFlowException")
