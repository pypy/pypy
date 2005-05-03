"""


"""
from pypy.interpreter.gateway import interp2app, ObjSpace, Arguments, W_Root 
from pypy.interpreter.baseobjspace import BaseWrappable, Wrappable
from pypy.interpreter.error import OperationError
from pypy.tool.cache import Cache
from pypy.tool.compile import compile2
import new

class TypeDef:
    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only"
        self.name = __name
        self.base = __base
        self.hasdict = '__dict__' in rawdict
        if __base is not None:
            self.hasdict |= __base.hasdict
        self.rawdict = rawdict
        self.acceptable_as_base_class = True


unique_interplevel_subclass_cache = Cache()
def get_unique_interplevel_subclass(cls, hasdict, wants_slots):
    return unique_interplevel_subclass_cache.getorbuild((cls, hasdict, wants_slots), _buildusercls, None)

def _buildusercls((cls, hasdict, wants_slots), ignored):
    "NOT_RPYTHON: initialization-time only"
    typedef = cls.typedef
    name = ['User']
    if not hasdict:
        name.append('NoDict')
    if wants_slots:
        name.append('WithSlots')
    name.append(cls.__name__)

    name = ''.join(name)

    body = {}

    no_extra_dict = typedef.hasdict or not hasdict

    class User_InsertNameHere(object):

        def getclass(self, space):
            return self.w__class__

        def setclass(self, w_subtype):
            # XXX sanity checks here
            self.w__class__ = w_subtype

        def __del__(self):
            self.space.userdel(self)

        if wants_slots:
            def user_setup_slots(self, nslots):
                self.slots_w = [None] * nslots 
        else:
            def user_setup_slots(self, nslots):
                assert nslots == 0

        if no_extra_dict:
            def user_setup(self, space, w_subtype, nslots):
                self.space = space
                self.w__class__ = w_subtype
                self.user_setup_slots(nslots)

        else:
            def getdict(self):
                return self.w__dict__

            def setdict(self, w_dict):
                space = self.space
                if not space.is_true(space.isinstance(w_dict, space.w_dict)):
                    raise OperationError(space.w_TypeError,
                            space.wrap("setting dictionary to a non-dict"))
                self.w__dict__ = w_dict

            def user_setup(self, space, w_subtype, nslots):
                self.space = space
                self.w__class__ = w_subtype
                self.w__dict__ = space.newdict([])
                self.user_setup_slots(nslots)

    body = dict([(key, value)
                 for key, value in User_InsertNameHere.__dict__.items()
                 if not key.startswith('_') or key == '__del__'])
    if not hasdict and not wants_slots:
        subcls = type(name, (cls,), body)
    else:
        basesubcls = get_unique_interplevel_subclass(cls, False, False)
        subcls = type(name, (basesubcls,), body)

    return subcls

def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return object.__new__(cls)
    else:
        return new.instance(cls)

def make_descr_typecheck_wrapper(func, extraargs=(), cls=None):
    if func is None:
        return None
    if hasattr(func, 'im_func'):
        assert not cls or cls is func.im_class
        cls = func.im_class
        func = func.im_func
    if not cls:
        #print "UNCHECKED", func.__module__ or '?', func.__name__
        return func

    miniglobals = {
         func.__name__: func,
        'OperationError': OperationError
        }
    if isinstance(cls, str):
        #print "<CHECK", func.__module__ or '?', func.__name__
        assert cls.startswith('<'),"pythontype typecheck should begin with <"
        unwrap = "w_obj"
        cls_name = cls[1:]
        expected = repr(cls_name)
        check = "space.is_true(space.isinstance(obj, space.w_%s))" % cls_name
    else:
        cls_name = cls.__name__
        if issubclass(cls, BaseWrappable):
            unwrap =  "space.interpclass_w(w_obj)"
        else:
            unwrap = "w_obj"
        miniglobals[cls_name] = cls
        check = "isinstance(obj, %s)" % cls_name
        expected = "%s.typedef.name" % cls_name
    
    source = """if 1: 
        def descr_typecheck_%(name)s(space, w_obj, %(extra)s):
            obj = %(unwrap)s
            if obj is None or not %(check)s:
                # xxx improve msg
                msg =  "descriptor is for '%%s'" %% %(expected)s
                raise OperationError(space.w_TypeError, space.wrap(msg))
            return %(name)s(space, obj, %(extra)s)
        \n""" % {'name': func.__name__, 
                 'check': check,
                 'expected': expected,
                 'unwrap': unwrap,
                 'extra': ', '.join(extraargs)} 
    exec compile2(source) in miniglobals
    return miniglobals['descr_typecheck_%s' % func.__name__]    


class GetSetProperty(Wrappable):
    def __init__(self, fget, fset=None, fdel=None, doc=None, cls=None):
        "NOT_RPYTHON: initialization-time only"
        fget = make_descr_typecheck_wrapper(fget, cls=cls) 
        fset = make_descr_typecheck_wrapper(fset, ('w_value',), cls=cls)
        fdel = make_descr_typecheck_wrapper(fdel, cls=cls) 
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc

    def descr_property_get(space, property, w_obj, w_cls=None):
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if w_obj == space.w_None and not space.is_true(space.is_(w_cls, space.type(space.w_None))):
            #print property, w_obj, w_cls
            return space.wrap(property)
        else:
            return property.fget(space, w_obj)

    def descr_property_set(space, property, w_obj, w_value):
        fset = property.fset
        if fset is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("read-only attribute"))
        fset(space, w_obj, w_value)

    def descr_property_del(space, property, w_obj):
        fdel = property.fdel
        if fdel is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("cannot delete attribute"))
        fdel(space, w_obj)

GetSetProperty.typedef = TypeDef(
    "GetSetProperty",
    __get__ = interp2app(GetSetProperty.descr_property_get.im_func,
                         unwrap_spec = [ObjSpace,
                                        GetSetProperty, W_Root, W_Root]),
    __set__ = interp2app(GetSetProperty.descr_property_set.im_func,
                         unwrap_spec = [ObjSpace,
                                        GetSetProperty, W_Root, W_Root]),
    __delete__ = interp2app(GetSetProperty.descr_property_del.im_func,
                            unwrap_spec = [ObjSpace,
                                           GetSetProperty, W_Root]),
    )

def interp_attrproperty(name, cls):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget, cls=cls)

def interp_attrproperty_w(name, cls):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        w_value = getattr(obj, name)
        if w_value is None:
            return space.w_None
        else:
            return w_value 

    return GetSetProperty(fget, cls=cls)

class Member(Wrappable):
    """For slots."""
    def __init__(self, index, name, w_cls):
        self.index = index
        self.name = name
        self.w_cls = w_cls

    def typecheck(self, space, w_obj):
        if not space.is_true(space.isinstance(w_obj, self.w_cls)):
            raise OperationError(space.w_TypeError,
                                 space.wrap("descriptor '%s' for '%s' objects doesn't apply to '%s' object" %
                                            (self.name, self.w_cls.name, space.type(w_obj).name)))

    def descr_member_get(space, member, w_obj, w_w_cls=None):
        if space.is_w(w_obj, space.w_None):
            return space.wrap(member)
        else:
            self = member
            self.typecheck(space, w_obj)
            w_result = w_obj.slots_w[self.index]
            if w_result is None:
                raise OperationError(space.w_AttributeError,
                                     space.wrap(self.name)) # XXX better message
            return w_result

    def descr_member_set(space, member, w_obj, w_value):
        self = member
        self.typecheck(space, w_obj)
        w_obj.slots_w[self.index] = w_value

    def descr_member_del(space, member, w_obj):
        self = member
        self.typecheck(space, w_obj)
        w_obj.slots_w[self.index] = None

Member.typedef = TypeDef(
    "Member",
    __get__ = interp2app(Member.descr_member_get.im_func,
                         unwrap_spec = [ObjSpace,
                                        Member, W_Root, W_Root]),
    __set__ = interp2app(Member.descr_member_set.im_func,
                         unwrap_spec = [ObjSpace,
                                        Member, W_Root, W_Root]),
    __delete__ = interp2app(Member.descr_member_del.im_func,
                            unwrap_spec = [ObjSpace,
                                           Member, W_Root]),
    )

# ____________________________________________________________
#
# Definition of the type's descriptors for all the internal types

from pypy.interpreter.eval import Code, Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame, ControlFlowException
from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, Method, StaticMethod
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator 
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.special import NotImplemented, Ellipsis

def descr_get_dict(space, obj):
    w_dict = obj.getdict()
    assert w_dict is not None, repr(obj)
    return w_dict

def descr_get_dict_may_be_None(space, obj):
    w_dict = obj.getdict()
    if w_dict is None:
        return space.w_None
    return w_dict

def descr_set_dict(space, obj, w_dict):
    obj.setdict(w_dict)

def generic_ne(space, w_obj1, w_obj2):
    if space.eq_w(w_obj1, w_obj2):
        return space.w_False
    else:
        return space.w_True
descr_generic_ne = interp2app(generic_ne)

# co_xxx interface emulation for built-in code objects
def fget_co_varnames(space, code): # unwrapping through unwrap_spec
    return space.newtuple([space.wrap(name) for name in code.getvarnames()])

def fget_co_argcount(space, code): # unwrapping through unwrap_spec
    argnames, varargname, kwargname = code.signature()
    return space.wrap(len(argnames))

def fget_co_flags(space, code): # unwrapping through unwrap_spec
    argnames, varargname, kwargname = code.signature()
    flags = 0
    if varargname is not None: flags |= CO_VARARGS
    if kwargname  is not None: flags |= CO_VARKEYWORDS
    return space.wrap(flags)

def fget_co_consts(space, code): # unwrapping through unwrap_spec
    w_docstring = space.wrap(code.getdocstring())
    return space.newtuple([w_docstring])

Code.typedef = TypeDef('internal-code',
    co_name = interp_attrproperty('co_name', cls=Code),
    co_varnames = GetSetProperty(fget_co_varnames, cls=Code),
    co_argcount = GetSetProperty(fget_co_argcount, cls=Code),
    co_flags = GetSetProperty(fget_co_flags, cls=Code),
    co_consts = GetSetProperty(fget_co_consts, cls=Code),
    )

Frame.typedef = TypeDef('internal-frame',
    f_code = interp_attrproperty('code', cls=Frame),
    f_locals = GetSetProperty(Frame.fget_getdictscope),
    f_globals = interp_attrproperty_w('w_globals', cls=Frame),
    )

PyCode.typedef = TypeDef('code',
    __new__ = interp2app(PyCode.descr_code__new__.im_func),
    __eq__ = interp2app(PyCode.descr_code__eq__),
    __ne__ = descr_generic_ne,
    co_argcount = interp_attrproperty('co_argcount', cls=PyCode),
    co_nlocals = interp_attrproperty('co_nlocals', cls=PyCode),
    co_stacksize = interp_attrproperty('co_stacksize', cls=PyCode),
    co_flags = interp_attrproperty('co_flags', cls=PyCode),
    co_code = interp_attrproperty('co_code', cls=PyCode),
    co_consts = GetSetProperty(PyCode.fget_co_consts),
    co_names = GetSetProperty(PyCode.fget_co_names),
    co_varnames =  GetSetProperty(PyCode.fget_co_varnames),
    co_freevars =  GetSetProperty(PyCode.fget_co_freevars),
    co_cellvars =  GetSetProperty(PyCode.fget_co_cellvars),
    co_filename = interp_attrproperty('co_filename', cls=PyCode),
    co_name = interp_attrproperty('co_name', cls=PyCode),
    co_firstlineno = interp_attrproperty('co_firstlineno', cls=PyCode),
    co_lnotab = interp_attrproperty('co_lnotab', cls=PyCode),
    )

PyFrame.typedef = TypeDef('frame',
    f_builtins = GetSetProperty(PyFrame.fget_f_builtins),
    f_lineno = GetSetProperty(PyFrame.fget_f_lineno, PyFrame.fset_f_lineno),
    f_back = GetSetProperty(PyFrame.fget_f_back),
    f_lasti = GetSetProperty(PyFrame.fget_f_lasti),
    f_trace = GetSetProperty(PyFrame.fget_f_trace, PyFrame.fset_f_trace),
    f_exc_type = GetSetProperty(PyFrame.fget_f_exc_type),
    f_exc_value = GetSetProperty(PyFrame.fget_f_exc_value),
    f_exc_traceback = GetSetProperty(PyFrame.fget_f_exc_traceback),
    f_restricted = GetSetProperty(PyFrame.fget_f_restricted),
    **Frame.typedef.rawdict)

Module.typedef = TypeDef("module",
    __new__ = interp2app(Module.descr_module__new__.im_func,
                         unwrap_spec=[ObjSpace, W_Root, Arguments]),
    __init__ = interp2app(Module.descr_module__init__),
    __dict__ = GetSetProperty(descr_get_dict_may_be_None, cls=Module), # module dictionaries are readonly attributes
    __doc__ = 'module(name[, doc])\n\nCreate a module object.\nThe name must be a string; the optional doc argument can have any type.'
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

getset_func_dict = GetSetProperty(descr_get_dict, descr_set_dict, cls=Function)

Function.typedef = TypeDef("function",
    __new__ = interp2app(Function.descr_method__new__.im_func),                           
    __call__ = interp2app(Function.descr_function_call,
                          unwrap_spec=['self', Arguments]),
    __get__ = interp2app(Function.descr_function_get),
    func_code = getset_func_code, 
    func_doc = getset_func_doc,
    func_name = interp_attrproperty('name', cls=Function), 
    func_dict = getset_func_dict, 
    func_defaults = getset_func_defaults,
    func_globals = interp_attrproperty_w('w_func_globals', cls=Function),
    func_closure = GetSetProperty( Function.fget_func_closure ),
    __doc__ = getset_func_doc,
    __name__ = interp_attrproperty('name', cls=Function),
    __dict__ = getset_func_dict,
    __module__ = getset___module__,
    # XXX func_closure, etc.pp
    )

Method.typedef = TypeDef("method",
    __new__ = interp2app(Method.descr_method__new__.im_func),
    __call__ = interp2app(Method.descr_method_call,
                          unwrap_spec=['self', Arguments]),
    __get__ = interp2app(Method.descr_method_get),
    im_func  = interp_attrproperty_w('w_function', cls=Method), 
    im_self  = interp_attrproperty_w('w_instance', cls=Method), 
    im_class = interp_attrproperty_w('w_class', cls=Method),
    __getattribute__ = interp2app(Method.descr_method_getattribute),
    __eq__ = interp2app(Method.descr_method_eq),
    __ne__ = descr_generic_ne,
    # XXX getattribute/setattribute etc.pp 
    )

StaticMethod.typedef = TypeDef("staticmethod",
    __get__ = interp2app(StaticMethod.descr_staticmethod_get),
    # XXX getattribute etc.pp
    )

def always_none(self, obj):
    return None
BuiltinFunction.typedef = TypeDef("builtin_function",**Function.typedef.rawdict)
BuiltinFunction.typedef.rawdict.update({
    '__new__': interp2app(BuiltinFunction.descr_method__new__.im_func),
    '__self__': GetSetProperty(always_none, cls=BuiltinFunction)
    })
del BuiltinFunction.typedef.rawdict['__get__']

PyTraceback.typedef = TypeDef("traceback",
    tb_frame  = interp_attrproperty('frame', cls=PyTraceback),
    tb_lasti  = interp_attrproperty('lasti', cls=PyTraceback),
    tb_lineno = interp_attrproperty('lineno', cls=PyTraceback),
    tb_next   = interp_attrproperty('next', cls=PyTraceback),
    )

GeneratorIterator.typedef = TypeDef("generator",
    next       = interp2app(GeneratorIterator.descr_next),
    __iter__   = interp2app(GeneratorIterator.descr__iter__),
    gi_running = interp_attrproperty('running', cls=GeneratorIterator), 
    gi_frame   = interp_attrproperty('frame', cls=GeneratorIterator), 
)

Cell.typedef = TypeDef("cell")

Ellipsis.typedef = TypeDef("Ellipsis", 
    __repr__   = interp2app(Ellipsis.descr__repr__),
)

NotImplemented.typedef = TypeDef("NotImplemented", 
    __repr__   = interp2app(NotImplemented.descr__repr__), 
)

ControlFlowException.typedef = TypeDef("ControlFlowException")


interptypes = [ val.typedef for name,val in globals().items() if hasattr(val,'__bases__') and hasattr(val,'typedef')  ]

    
