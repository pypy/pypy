"""


"""
import py
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import Wrappable, W_Root, ObjSpace, \
    DescrMismatch
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.rlib.objectmodel import instantiate
from pypy.rlib.rarithmetic import intmask

class TypeDef:
    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only"
        self.name = __name
        self.base = __base
        self.hasdict = '__dict__' in rawdict
        self.weakrefable = '__weakref__' in rawdict
        self.custom_hash = '__hash__' in rawdict
        if __base is not None:
            self.hasdict     |= __base.hasdict
            self.weakrefable |= __base.weakrefable
            self.custom_hash |= __base.custom_hash
            # NB. custom_hash is sometimes overridden manually by callers
        self.rawdict = {}
        self.acceptable_as_base_class = True
        # xxx used by faking
        self.fakedcpytype = None
        self.add_entries(**rawdict)
    
    def add_entries(self, **rawdict):
        # xxx fix the names of the methods to match what app-level expects
        for key, value in rawdict.items():
            if isinstance(value, (interp2app, GetSetProperty)):
                value.name = key
        self.rawdict.update(rawdict)
    
    def _freeze_(self):
        # hint for the annotator: track individual constant instances of TypeDef
        return True


# ____________________________________________________________
#  Hash support

def get_default_hash_function(cls):
    # go to the first parent class of 'cls' that as a typedef
    while 'typedef' not in cls.__dict__:
        cls = cls.__bases__[0]
        if cls is object:
            # not found: 'cls' must have been an abstract class,
            # no hash function is needed
            return None
    if cls.typedef.custom_hash:
        return None   # the typedef says that instances have their own
                      # hash, so we don't need a default RPython-level
                      # hash function.
    try:
        hashfunction = _hashfunction_cache[cls]
    except KeyError:
        def hashfunction(w_obj):
            "Return the identity hash of 'w_obj'."
            assert isinstance(w_obj, cls)
            return hash(w_obj)   # forces a hash_cache only on 'cls' instances
        hashfunction = func_with_new_name(hashfunction,
                                       'hashfunction_for_%s' % (cls.__name__,))
        _hashfunction_cache[cls] = hashfunction
    return hashfunction
get_default_hash_function._annspecialcase_ = 'specialize:memo'
_hashfunction_cache = {}

def default_identity_hash(space, w_obj):
    fn = get_default_hash_function(w_obj.__class__)
    if fn is None:
        typename = space.type(w_obj).getname(space, '?')
        msg = "%s objects have no default hash" % (typename,)
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return space.wrap(intmask(fn(w_obj)))

def descr__hash__unhashable(space, w_obj):
    typename = space.type(w_obj).getname(space, '?')
    msg = "%s objects are unhashable" % (typename,)
    raise OperationError(space.w_TypeError,space.wrap(msg))

no_hash_descr = interp2app(descr__hash__unhashable)

# ____________________________________________________________
def get_unique_interplevel_subclass(cls, hasdict, wants_slots, needsdel=False,
                                    weakrefable=False):
    if needsdel:
        hasdict = wants_slots = weakrefable = True
    if hasdict:
        weakrefable = True
    else:
        wants_slots = True
    return  _get_unique_interplevel_subclass(cls, hasdict, wants_slots, needsdel, weakrefable)
get_unique_interplevel_subclass._annspecialcase_ = "specialize:memo"

def _get_unique_interplevel_subclass(cls, hasdict, wants_slots, needsdel, weakrefable):
    "NOT_RPYTHON: initialization-time only"    
    typedef = cls.typedef    
    if hasdict and typedef.hasdict:
        hasdict = False
    if weakrefable and typedef.weakrefable:
        weakrefable = False

    key = cls, hasdict, wants_slots, needsdel, weakrefable
    try:
        return _subclass_cache[key]
    except KeyError:
        subcls = _buildusercls(cls, hasdict, wants_slots, needsdel, weakrefable)
        _subclass_cache[key] = subcls
        return subcls
_subclass_cache = {}

def _buildusercls(cls, hasdict, wants_slots, wants_del, weakrefable):
    "NOT_RPYTHON: initialization-time only"
    name = ['User']
    if not hasdict:
        name.append('NoDict')
    if wants_slots:
        name.append('WithSlots')
    if wants_del:
        name.append('WithDel')
    if weakrefable:
        name.append('Weakrefable')
    
    name.append(cls.__name__)
    
    name = ''.join(name)
    if weakrefable:
        supercls = _get_unique_interplevel_subclass(cls, hasdict, wants_slots,
                                                   wants_del, False)
        class Proto(object):
            _lifeline_ = None
            def getweakref(self):
                return self._lifeline_
            def setweakref(self, space, weakreflifeline):
                self._lifeline_ = weakreflifeline
    elif wants_del:
        supercls = _get_unique_interplevel_subclass(cls, hasdict, wants_slots,
                                                   False, False)
        parent_destructor = getattr(cls, '__del__', None)
        class Proto(object):
            def __del__(self):
                try:
                    self.space.userdel(self)
                except OperationError, e:
                    e.write_unraisable(self.space, 'method __del__ of ', self)
                    e.clear(self.space)   # break up reference cycles
                if parent_destructor is not None:
                    parent_destructor(self)
    elif wants_slots:
        supercls = _get_unique_interplevel_subclass(cls, hasdict, False, False, False)
        
        class Proto(object):
            slots_w = []
            def user_setup_slots(self, nslots):
                if nslots > 0:
                    self.slots_w = [None] * nslots
            
            def setslotvalue(self, index, w_value):
                self.slots_w[index] = w_value
            
            def getslotvalue(self, index):
                return self.slots_w[index]
    elif hasdict:
        supercls = _get_unique_interplevel_subclass(cls, False, False, False, False)
        
        class Proto(object):
            def getdict(self):
                return self.w__dict__
            
            def setdict(self, space, w_dict):
                if not space.is_true(space.isinstance(w_dict, space.w_dict)):
                    raise OperationError(space.w_TypeError,
                            space.wrap("setting dictionary to a non-dict"))
                if space.config.objspace.std.withmultidict:
                    from pypy.objspace.std import dictmultiobject
                    assert isinstance(w_dict, dictmultiobject.W_DictMultiObject)
                self.w__dict__ = w_dict
            
            def user_setup(self, space, w_subtype):
                self.space = space
                self.w__class__ = w_subtype
                if space.config.objspace.std.withsharingdict:
                    from pypy.objspace.std import dictmultiobject
                    self.w__dict__ = dictmultiobject.W_DictMultiObject(space,
                            sharing=True)
                elif space.config.objspace.std.withshadowtracking:
                    from pypy.objspace.std import dictmultiobject
                    self.w__dict__ = dictmultiobject.W_DictMultiObject(space)
                    self.w__dict__.implementation = \
                        dictmultiobject.ShadowDetectingDictImplementation(
                                space, w_subtype)
                else:
                    self.w__dict__ = space.newdict()
                self.user_setup_slots(w_subtype.nslots)

            def setclass(self, space, w_subtype):
                # only used by descr_set___class__
                self.w__class__ = w_subtype
                if space.config.objspace.std.withshadowtracking:
                    self.w__dict__.implementation.set_shadows_anything()

            def getdictvalue_attr_is_in_class(self, space, w_name):
                w_dict = self.w__dict__
                if space.config.objspace.std.withshadowtracking:
                    if not w_dict.implementation.shadows_anything():
                        return None
                return space.finditem(w_dict, w_name)
            
    else:
        supercls = cls
        
        class Proto(object):
            
            def getclass(self, space):
                return self.w__class__
            
            def setclass(self, space, w_subtype):

                # only used by descr_set___class__
                self.w__class__ = w_subtype
            
            
            def user_setup(self, space, w_subtype):
                self.space = space
                self.w__class__ = w_subtype
                self.user_setup_slots(w_subtype.nslots)
            
            def user_setup_slots(self, nslots):
                assert nslots == 0
    
    body = dict([(key, value)
                 for key, value in Proto.__dict__.items()
                 if not key.startswith('__') or key == '__del__'])
    subcls = type(name, (supercls,), body)
    return subcls

def make_descr_typecheck_wrapper(func, extraargs=(), cls=None):
    if func is None:
        return None
    if cls is None:
        return func
    if hasattr(func, 'im_func'):
        assert func.im_class is cls
        func = func.im_func
    
    miniglobals = {
         func.__name__: func,
        'OperationError': OperationError
        }
    if isinstance(cls, str):
        #print "<CHECK", func.__module__ or '?', func.__name__
        assert cls.startswith('<'),"pythontype typecheck should begin with <"
        source = """
        def descr_typecheck_%(name)s(space, w_obj, %(extra)s):
            if not space.is_true(space.isinstance(w_obj, space.w_%(cls_name)s)):
                # xxx improve msg
                msg =  "descriptor is for '%(expected)s'"
                raise OperationError(space.w_TypeError, space.wrap(msg))
            return %(name)s(space, w_obj, %(extra)s)
        """
        cls_name = cls[1:]
        expected = repr(cls_name)
    else:
        cls_name = cls.__name__
        assert issubclass(cls, Wrappable)
        source = """
        def descr_typecheck_%(name)s(space, w_obj, %(extra)s):
            obj = space.descr_self_interp_w(%(cls_name)s, w_obj)
            return %(name)s(space, obj, %(extra)s)
        """
        miniglobals[cls_name] = cls
    
    name = func.__name__
    extra = ', '.join(extraargs)
    source = py.code.Source(source % locals())
    exec source.compile() in miniglobals
    return miniglobals['descr_typecheck_%s' % func.__name__]

def unknown_objclass_getter(space):
    raise OperationError(space.w_TypeError,
                         space.wrap("generic property has no __objclass__"))

def make_objclass_getter(func, cls, cache={}):
    if hasattr(func, 'im_func'):
        assert not cls or cls is func.im_class
        cls = func.im_class
    if not cls:
        return unknown_objclass_getter, cls
    try:
        return cache[cls]
    except KeyError:
        pass
    miniglobals = {}
    if isinstance(cls, str):
        assert cls.startswith('<'),"pythontype typecheck should begin with <"
        cls_name = cls[1:]
        typeexpr = "space.w_%s" % cls_name
    else:
        miniglobals['cls'] = cls
        typeexpr = "space.gettypeobject(cls.typedef)"
    source = """if 1:
        def objclass_getter(space):
            return %s
        \n""" % (typeexpr,)
    exec compile2(source) in miniglobals
    res = miniglobals['objclass_getter'], cls
    cache[cls] = res
    return res

class GetSetProperty(Wrappable):
    def __init__(self, fget, fset=None, fdel=None, doc=None, cls=None):
        "NOT_RPYTHON: initialization-time only"
        objclass_getter, cls = make_objclass_getter(fget, cls)
        fget = make_descr_typecheck_wrapper(fget, cls=cls)
        fset = make_descr_typecheck_wrapper(fset, ('w_value',), cls=cls)
        fdel = make_descr_typecheck_wrapper(fdel, cls=cls)
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc
        self.reqcls = cls
        self.name = '<generic property>'
        self.objclass_getter = objclass_getter
    
    def descr_property_get(space, property, w_obj, w_cls=None):
        """property.__get__(obj[, type]) -> value
        Read the value of the property of the given obj."""
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if (space.is_w(w_obj, space.w_None)
            and not space.is_w(w_cls, space.type(space.w_None))):
            #print property, w_obj, w_cls
            return space.wrap(property)
        else:
            try:
                return property.fget(space, w_obj)
            except DescrMismatch, e:
                return w_obj.descr_call_mismatch(space, '__getattribute__',\
                    property.reqcls, Arguments(space, [w_obj,
                                           space.wrap(property.name)]))
    
    def descr_property_set(space, property, w_obj, w_value):
        """property.__set__(obj, value)
        Change the value of the property of the given obj."""
        fset = property.fset
        if fset is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("readonly attribute"))
        try:
            fset(space, w_obj, w_value)
        except DescrMismatch, e:
            w_obj.descr_call_mismatch(space, '__setattr__',\
                property.reqcls, Arguments(space, [w_obj,
                space.wrap(property.name), w_value]))
    
    def descr_property_del(space, property, w_obj):
        """property.__delete__(obj)
        Delete the value of the property from the given obj."""
        fdel = property.fdel
        if fdel is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("cannot delete attribute"))
        try:
            fdel(space, w_obj)
        except DescrMismatch, e:
            w_obj.descr_call_mismatch(space, '__delattr__',\
                property.reqcls, Arguments(space, [w_obj,
                space.wrap(property.name)]))
    
    def descr_get_objclass(space, property):
        return property.objclass_getter(space)

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

GetSetProperty.typedef = TypeDef(
    "getset_descriptor",
    __get__ = interp2app(GetSetProperty.descr_property_get.im_func,
                         unwrap_spec = [ObjSpace,
                                        GetSetProperty, W_Root, W_Root]),
    __set__ = interp2app(GetSetProperty.descr_property_set.im_func,
                         unwrap_spec = [ObjSpace,
                                        GetSetProperty, W_Root, W_Root]),
    __delete__ = interp2app(GetSetProperty.descr_property_del.im_func,
                            unwrap_spec = [ObjSpace,
                                           GetSetProperty, W_Root]),
    __name__ = interp_attrproperty('name', cls=GetSetProperty),
    __objclass__ = GetSetProperty(GetSetProperty.descr_get_objclass),
    )


class Member(Wrappable):
    """For slots."""
    def __init__(self, index, name, w_cls):
        self.index = index
        self.name = name
        self.w_cls = w_cls
    
    def typecheck(self, space, w_obj):
        if not space.is_true(space.isinstance(w_obj, self.w_cls)):
            raise OperationError(space.w_TypeError,
                              space.wrap("descriptor '%s' for '%s'"
                              " objects doesn't apply to '%s' object" %
                                   (self.name,
                                    self.w_cls.name,
                                    space.type(w_obj).getname(space, '?'))))
    
    def descr_member_get(space, member, w_obj, w_w_cls=None):
        """member.__get__(obj[, type]) -> value
        Read the slot 'member' of the given 'obj'."""
        if space.is_w(w_obj, space.w_None):
            return space.wrap(member)
        else:
            self = member
            self.typecheck(space, w_obj)
            w_result = w_obj.getslotvalue(self.index)
            if w_result is None:
                raise OperationError(space.w_AttributeError,
                                     space.wrap(self.name)) # XXX better message
            return w_result
    
    def descr_member_set(space, member, w_obj, w_value):
        """member.__set__(obj, value)
        Write into the slot 'member' of the given 'obj'."""
        self = member
        self.typecheck(space, w_obj)
        w_obj.setslotvalue(self.index, w_value)
    
    def descr_member_del(space, member, w_obj):
        """member.__delete__(obj)
        Delete the value of the slot 'member' from the given 'obj'."""
        self = member
        self.typecheck(space, w_obj)
        w_obj.setslotvalue(self.index, None)

Member.typedef = TypeDef(
    "member_descriptor",
    __get__ = interp2app(Member.descr_member_get.im_func,
                         unwrap_spec = [ObjSpace,
                                        Member, W_Root, W_Root]),
    __set__ = interp2app(Member.descr_member_set.im_func,
                         unwrap_spec = [ObjSpace,
                                        Member, W_Root, W_Root]),
    __delete__ = interp2app(Member.descr_member_del.im_func,
                            unwrap_spec = [ObjSpace,
                                           Member, W_Root]),
    __name__ = interp_attrproperty('name', cls=Member),
    __objclass__ = interp_attrproperty_w('w_cls', cls=Member),
    )

# ____________________________________________________________
#
# Definition of the type's descriptors for all the internal types

from pypy.interpreter.eval import Code, Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pyopcode import SuspendedUnroller
from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, Method, StaticMethod
from pypy.interpreter.function import BuiltinFunction, descr_function_get
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.special import NotImplemented, Ellipsis

def descr_get_dict(space, w_obj):
    w_dict = w_obj.getdict()
    if w_dict is None:
        typename = space.type(w_obj).getname(space, '?')
        raise OperationError(space.w_TypeError,
                             space.wrap("descriptor '__dict__' doesn't apply to"
                                        " '%s' objects" % typename))
    return w_dict

def descr_set_dict(space, w_obj, w_dict):
    w_obj.setdict(space, w_dict)

def descr_get_weakref(space, w_obj):
    lifeline = w_obj.getweakref()
    if lifeline is None:
        return space.w_None
    return lifeline.get_any_weakref(space)

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
    w_docstring = code.getdocstring(space)
    return space.newtuple([w_docstring])

weakref_descr = GetSetProperty(descr_get_weakref)
weakref_descr.name = '__weakref__'

def make_weakref_descr(cls):
    # force the interface into the given cls
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline
    cls._lifeline_ = None
    cls.getweakref = getweakref
    cls.setweakref = setweakref
    return weakref_descr


Code.typedef = TypeDef('internal-code',
    co_name = interp_attrproperty('co_name', cls=Code),
    co_varnames = GetSetProperty(fget_co_varnames, cls=Code),
    co_argcount = GetSetProperty(fget_co_argcount, cls=Code),
    co_flags = GetSetProperty(fget_co_flags, cls=Code),
    co_consts = GetSetProperty(fget_co_consts, cls=Code),
    )

Frame.typedef = TypeDef('internal-frame',
    f_code = GetSetProperty(Frame.fget_code),
    f_locals = GetSetProperty(Frame.fget_getdictscope),
    f_globals = interp_attrproperty_w('w_globals', cls=Frame),
    )

PyCode.typedef = TypeDef('code',
    __new__ = interp2app(PyCode.descr_code__new__.im_func),
    __eq__ = interp2app(PyCode.descr_code__eq__),
    __ne__ = descr_generic_ne,
    __hash__ = interp2app(PyCode.descr_code__hash__),
    __reduce__   = interp2app(PyCode.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
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
    __reduce__   = interp2app(PyFrame.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(PyFrame.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    f_builtins = GetSetProperty(PyFrame.fget_f_builtins),
    f_lineno = GetSetProperty(PyFrame.fget_f_lineno, PyFrame.fset_f_lineno),
    f_back = GetSetProperty(PyFrame.fget_f_back),
    f_lasti = GetSetProperty(PyFrame.fget_f_lasti),
    f_trace = GetSetProperty(PyFrame.fget_f_trace, PyFrame.fset_f_trace,
                             PyFrame.fdel_f_trace),
    f_exc_type = GetSetProperty(PyFrame.fget_f_exc_type),
    f_exc_value = GetSetProperty(PyFrame.fget_f_exc_value),
    f_exc_traceback = GetSetProperty(PyFrame.fget_f_exc_traceback),
    f_restricted = GetSetProperty(PyFrame.fget_f_restricted),
    **Frame.typedef.rawdict)

Module.typedef = TypeDef("module",
    __new__ = interp2app(Module.descr_module__new__.im_func,
                         unwrap_spec=[ObjSpace, W_Root, Arguments]),
    __init__ = interp2app(Module.descr_module__init__),
    __reduce__ = interp2app(Module.descr__reduce__,
                            unwrap_spec=['self', ObjSpace]),
    __dict__ = GetSetProperty(descr_get_dict, cls=Module), # module dictionaries are readonly attributes
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
getset_func_name = GetSetProperty(Function.fget_func_name,
                                  Function.fset_func_name)

getset_func_dict = GetSetProperty(descr_get_dict, descr_set_dict, cls=Function)

Function.typedef = TypeDef("function",
    __new__ = interp2app(Function.descr_method__new__.im_func),
    __call__ = interp2app(Function.descr_function_call,
                          unwrap_spec=['self', Arguments],
                          descrmismatch='__call__'),
    __get__ = interp2app(descr_function_get),
    __repr__ = interp2app(Function.descr_function_repr, descrmismatch='__repr__'),
    __reduce__ = interp2app(Function.descr_function__reduce__,
                            unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(Function.descr_function__setstate__,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    func_code = getset_func_code,
    func_doc = getset_func_doc,
    func_name = getset_func_name,
    func_dict = getset_func_dict,
    func_defaults = getset_func_defaults,
    func_globals = interp_attrproperty_w('w_func_globals', cls=Function),
    func_closure = GetSetProperty( Function.fget_func_closure ),
    __doc__ = getset_func_doc,
    __name__ = getset_func_name,
    __dict__ = getset_func_dict,
    __module__ = getset___module__,
    __weakref__ = make_weakref_descr(Function),
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
    __hash__ = interp2app(Method.descr_method_hash),
    __repr__ = interp2app(Method.descr_method_repr),
    __reduce__ = interp2app(Method.descr_method__reduce__,
                            unwrap_spec=['self', ObjSpace]),
    __weakref__ = make_weakref_descr(Method),
    )

StaticMethod.typedef = TypeDef("staticmethod",
    __get__ = interp2app(StaticMethod.descr_staticmethod_get),
    )

def always_none(self, obj):
    return None
BuiltinFunction.typedef = TypeDef("builtin_function",**Function.typedef.rawdict)
BuiltinFunction.typedef.rawdict.update({
    '__new__': interp2app(BuiltinFunction.descr_method__new__.im_func),
    '__self__': GetSetProperty(always_none, cls=BuiltinFunction),
    '__repr__': interp2app(BuiltinFunction.descr_function_repr),
    })
del BuiltinFunction.typedef.rawdict['__get__']

PyTraceback.typedef = TypeDef("traceback",
    __reduce__   = interp2app(PyTraceback.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(PyTraceback.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    tb_frame  = interp_attrproperty('frame', cls=PyTraceback),
    tb_lasti  = interp_attrproperty('lasti', cls=PyTraceback),
    tb_lineno = interp_attrproperty('lineno', cls=PyTraceback),
    tb_next   = interp_attrproperty('next', cls=PyTraceback),
    )

GeneratorIterator.typedef = TypeDef("generator",
    __reduce__   = interp2app(GeneratorIterator.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    next       = interp2app(GeneratorIterator.descr_next,
                            descrmismatch='next'),
    __iter__   = interp2app(GeneratorIterator.descr__iter__,
                            descrmismatch='__iter__'),
    gi_running = interp_attrproperty('running', cls=GeneratorIterator),
    gi_frame   = interp_attrproperty('frame', cls=GeneratorIterator),
    __weakref__ = make_weakref_descr(GeneratorIterator),
)

Cell.typedef = TypeDef("cell",
    __eq__       = interp2app(Cell.descr__eq__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
    __ne__       = descr_generic_ne,
    __hash__     = no_hash_descr,
    __reduce__   = interp2app(Cell.descr__reduce__,
                              unwrap_spec=['self', ObjSpace]),
    __setstate__ = interp2app(Cell.descr__setstate__,
                              unwrap_spec=['self', ObjSpace, W_Root]),
)

Ellipsis.typedef = TypeDef("Ellipsis",
    __repr__   = interp2app(Ellipsis.descr__repr__),
)

NotImplemented.typedef = TypeDef("NotImplemented",
    __repr__   = interp2app(NotImplemented.descr__repr__),
)

SuspendedUnroller.typedef = TypeDef("SuspendedUnroller")


interptypes = [ val.typedef for name,val in globals().items() if hasattr(val,'__bases__') and hasattr(val,'typedef')  ]
