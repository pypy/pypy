"""


"""
import py
from pypy.interpreter.gateway import interp2app, BuiltinCode
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import Wrappable, DescrMismatch
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.rlib.objectmodel import instantiate, compute_identity_hash, specialize
from pypy.rlib.jit import promote

class TypeDef:
    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only"
        self.name = __name
        self.base = __base
        self.hasdict = '__dict__' in rawdict
        self.weakrefable = '__weakref__' in rawdict
        self.doc = rawdict.pop('__doc__', None)
        if __base is not None:
            self.hasdict     |= __base.hasdict
            self.weakrefable |= __base.weakrefable
        self.rawdict = {}
        self.acceptable_as_base_class = '__new__' in rawdict
        self.applevel_subclasses_base = None
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

    def __repr__(self):
        return "<%s name=%r>" % (self.__class__.__name__, self.name)


# ____________________________________________________________
#  Hash support

def default_identity_hash(space, w_obj):
    return space.wrap(compute_identity_hash(w_obj))

# ____________________________________________________________
#
# For each built-in app-level type Xxx that can be subclassed at
# app-level, the corresponding interp-level W_XxxObject class cannot
# generally represent instances of app-level subclasses of Xxx.  The
# reason is that it is missing a place to store the __dict__, the slots,
# the weakref lifeline, and it typically has no interp-level __del__.
# So we create a few interp-level subclasses of W_XxxObject, which add
# some combination of features.
#
# We don't build 2**4 == 16 subclasses for all combinations of requested
# features, but limit ourselves to 6, chosen a bit arbitrarily based on
# typical usage (case 1 is the most common kind of app-level subclasses;
# case 2 is the memory-saving kind defined with __slots__).
#
#     dict   slots   del   weakrefable
#
# 1.    Y      N      N         Y          UserDictWeakref
# 2.    N      Y      N         N          UserSlots
# 3.    Y      Y      N         Y          UserDictWeakrefSlots
# 4.    N      Y      N         Y          UserSlotsWeakref
# 5.    Y      Y      Y         Y          UserDictWeakrefSlotsDel
# 6.    N      Y      Y         Y          UserSlotsWeakrefDel
#
# Note that if the app-level explicitly requests no dict, we should not
# provide one, otherwise storing random attributes on the app-level
# instance would unexpectedly work.  We don't care too much, though, if
# an object is weakrefable when it shouldn't really be.  It's important
# that it has a __del__ only if absolutely needed, as this kills the
# performance of the GCs.
#
# Interp-level inheritance is like this:
#
#        W_XxxObject base
#             /   \
#            1     2
#           /       \
#          3         4
#         /           \
#        5             6

def get_unique_interplevel_subclass(config, cls, hasdict, wants_slots,
                                    needsdel=False, weakrefable=False):
    "NOT_RPYTHON: initialization-time only"
    if hasattr(cls, '__del__') and getattr(cls, "handle_del_manually", False):
        needsdel = False
    assert cls.typedef.acceptable_as_base_class
    key = config, cls, hasdict, wants_slots, needsdel, weakrefable
    try:
        return _subclass_cache[key]
    except KeyError:
        subcls = _getusercls(config, cls, hasdict, wants_slots, needsdel,
                             weakrefable)
        assert key not in _subclass_cache
        _subclass_cache[key] = subcls
        return subcls
get_unique_interplevel_subclass._annspecialcase_ = "specialize:memo"
_subclass_cache = {}

def enum_interplevel_subclasses(config, cls):
    """Return a list of all the extra interp-level subclasses of 'cls' that
    can be built by get_unique_interplevel_subclass()."""
    result = []
    for flag1 in (False, True):
        for flag2 in (False, True):
            for flag3 in (False, True):
                for flag4 in (False, True):
                    result.append(get_unique_interplevel_subclass(
                        config, cls, flag1, flag2, flag3, flag4))
    result = dict.fromkeys(result)
    assert len(result) <= 6
    return result.keys()

def _getusercls(config, cls, wants_dict, wants_slots, wants_del, weakrefable):
    typedef = cls.typedef
    if wants_dict and typedef.hasdict:
        wants_dict = False
    if config.objspace.std.withmapdict and not typedef.hasdict:
        # mapdict only works if the type does not already have a dict
        if wants_del:
            parentcls = get_unique_interplevel_subclass(config, cls, True, True,
                                                        False, True)
            return _usersubclswithfeature(config, parentcls, "del")
        return _usersubclswithfeature(config, cls, "user", "dict", "weakref", "slots")
    # Forest of if's - see the comment above.
    if wants_del:
        if wants_dict:
            # case 5.  Parent class is 3.
            parentcls = get_unique_interplevel_subclass(config, cls, True, True,
                                                        False, True)
        else:
            # case 6.  Parent class is 4.
            parentcls = get_unique_interplevel_subclass(config, cls, False, True,
                                                        False, True)
        return _usersubclswithfeature(config, parentcls, "del")
    elif wants_dict:
        if wants_slots:
            # case 3.  Parent class is 1.
            parentcls = get_unique_interplevel_subclass(config, cls, True, False,
                                                        False, True)
            return _usersubclswithfeature(config, parentcls, "slots")
        else:
            # case 1 (we need to add weakrefable unless it's already in 'cls')
            if not typedef.weakrefable:
                return _usersubclswithfeature(config, cls, "user", "dict", "weakref")
            else:
                return _usersubclswithfeature(config, cls, "user", "dict")
    else:
        if weakrefable and not typedef.weakrefable:
            # case 4.  Parent class is 2.
            parentcls = get_unique_interplevel_subclass(config, cls, False, True,
                                                        False, False)
            return _usersubclswithfeature(config, parentcls, "weakref")
        else:
            # case 2 (if the base is already weakrefable, case 2 == case 4)
            return _usersubclswithfeature(config, cls, "user", "slots")

def _usersubclswithfeature(config, parentcls, *features):
    key = config, parentcls, features
    try:
        return _usersubclswithfeature_cache[key]
    except KeyError:
        subcls = _builduserclswithfeature(config, parentcls, *features)
        _usersubclswithfeature_cache[key] = subcls
        return subcls
_usersubclswithfeature_cache = {}
_allusersubcls_cache = {}

def _builduserclswithfeature(config, supercls, *features):
    "NOT_RPYTHON: initialization-time only"
    name = supercls.__name__
    name += ''.join([name.capitalize() for name in features])
    body = {}
    #print '..........', name, '(', supercls.__name__, ')'

    def add(Proto):
        for key, value in Proto.__dict__.items():
            if (not key.startswith('__') and not key.startswith('_mixin_') 
                    or key == '__del__'):
                if hasattr(value, "func_name"):
                    value = func_with_new_name(value, value.func_name)
                body[key] = value

    if (config.objspace.std.withmapdict and "dict" in features):
        from pypy.objspace.std.mapdict import BaseMapdictObject, ObjectMixin
        add(BaseMapdictObject)
        add(ObjectMixin)
        body["user_overridden_class"] = True
        features = ()

    if "user" in features:     # generic feature needed by all subcls

        class Proto(object):
            user_overridden_class = True

            def getclass(self, space):
                return promote(self.w__class__)

            def setclass(self, space, w_subtype):
                # only used by descr_set___class__
                self.w__class__ = w_subtype

            def user_setup(self, space, w_subtype):
                self.space = space
                self.w__class__ = w_subtype
                self.user_setup_slots(w_subtype.nslots)

            def user_setup_slots(self, nslots):
                assert nslots == 0
        add(Proto)

    if "weakref" in features:
        class Proto(object):
            _lifeline_ = None
            def getweakref(self):
                return self._lifeline_
            def setweakref(self, space, weakreflifeline):
                self._lifeline_ = weakreflifeline
            def delweakref(self):
                self._lifeline_ = None
        add(Proto)

    if "del" in features:
        parent_destructor = getattr(supercls, '__del__', None)
        def call_parent_del(self):
            assert isinstance(self, subcls)
            parent_destructor(self)
        def call_applevel_del(self):
            assert isinstance(self, subcls)
            self.space.userdel(self)
        class Proto(object):
            def __del__(self):
                self.clear_all_weakrefs()
                self.enqueue_for_destruction(self.space, call_applevel_del,
                                             'method __del__ of ')
                if parent_destructor is not None:
                    self.enqueue_for_destruction(self.space, call_parent_del,
                                                 'internal destructor of ')
        add(Proto)

    if "slots" in features:
        class Proto(object):
            slots_w = []
            def user_setup_slots(self, nslots):
                if nslots > 0:
                    self.slots_w = [None] * nslots
            def setslotvalue(self, index, w_value):
                self.slots_w[index] = w_value
            def getslotvalue(self, index):
                return self.slots_w[index]
        add(Proto)

    if "dict" in features:
        base_user_setup = supercls.user_setup.im_func
        if "user_setup" in body:
            base_user_setup = body["user_setup"]
        class Proto(object):
            def getdict(self, space):
                return self.w__dict__
            
            def setdict(self, space, w_dict):
                self.w__dict__ = check_new_dictionary(space, w_dict)
            
            def user_setup(self, space, w_subtype):
                self.w__dict__ = space.newdict(
                    instance=True, classofinstance=w_subtype)
                base_user_setup(self, space, w_subtype)

            def setclass(self, space, w_subtype):
                # only used by descr_set___class__
                self.w__class__ = w_subtype

        add(Proto)

    subcls = type(name, (supercls,), body)
    _allusersubcls_cache[subcls] = True
    return subcls

# a couple of helpers for the Proto classes above, factored out to reduce
# the translated code size
def check_new_dictionary(space, w_dict):
    if not space.is_true(space.isinstance(w_dict, space.w_dict)):
        raise OperationError(space.w_TypeError,
                space.wrap("setting dictionary to a non-dict"))
    from pypy.objspace.std import dictmultiobject
    assert isinstance(w_dict, dictmultiobject.W_DictMultiObject)
    return w_dict
check_new_dictionary._dont_inline_ = True

# ____________________________________________________________

@specialize.arg(0)
def make_descr_typecheck_wrapper(tag, func, extraargs=(), cls=None,
                                 use_closure=False):
    if func is None:
        return None
    return _make_descr_typecheck_wrapper(tag, func, extraargs, cls, use_closure)

@specialize.memo()
def _make_descr_typecheck_wrapper(tag, func, extraargs, cls, use_closure):
    # - if cls is None, the wrapped object is passed to the function
    # - if cls is a class, an unwrapped instance is passed
    # - if cls is a string, XXX unused?
    if cls is None and use_closure:
        return func
    if hasattr(func, 'im_func'):
        assert func.im_class is cls
        func = func.im_func

    miniglobals = {
         func.__name__: func,
        'OperationError': OperationError
        }
    if cls is None:
        source = """
        def descr_typecheck_%(name)s(closure, space, obj, %(extra)s):
            return %(name)s(%(args)s, %(extra)s)
        """
    else:
        cls_name = cls.__name__
        assert issubclass(cls, Wrappable)
        source = """
        def descr_typecheck_%(name)s(closure, space, w_obj, %(extra)s):
            obj = space.descr_self_interp_w(%(cls_name)s, w_obj)
            return %(name)s(%(args)s, %(extra)s)
        """
        miniglobals[cls_name] = cls
    
    name = func.__name__
    extra = ', '.join(extraargs)
    from pypy.interpreter import pycode
    argnames, _, _ = pycode.cpython_code_signature(func.func_code)
    if use_closure:
        if argnames[1] == 'space':
            args = "closure, space, obj"
        else:
            args = "closure, obj, space"
    else:
        if argnames[0] == 'space':
            args = "space, obj"
        else:
            args = "obj, space"
    source = py.code.Source(source % locals())
    exec source.compile() in miniglobals
    return miniglobals['descr_typecheck_%s' % func.__name__]

def unknown_objclass_getter(space):
    # NB. this is an AttributeError to make inspect.py happy
    raise OperationError(space.w_AttributeError,
                         space.wrap("generic property has no __objclass__"))

@specialize.arg(0)
def make_objclass_getter(tag, func, cls):
    if func and hasattr(func, 'im_func'):
        assert not cls or cls is func.im_class
        cls = func.im_class
    return _make_objclass_getter(cls)

@specialize.memo()
def _make_objclass_getter(cls):
    if not cls:
        return unknown_objclass_getter, cls
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
    return res

class GetSetProperty(Wrappable):
    _immutable_fields_ = ["fget", "fset", "fdel"]

    @specialize.arg(7)
    def __init__(self, fget, fset=None, fdel=None, doc=None,
                 cls=None, use_closure=False, tag=None):
        objclass_getter, cls = make_objclass_getter(tag, fget, cls)
        fget = make_descr_typecheck_wrapper((tag, 0), fget,
                                            cls=cls, use_closure=use_closure)
        fset = make_descr_typecheck_wrapper((tag, 1), fset, ('w_value',),
                                            cls=cls, use_closure=use_closure)
        fdel = make_descr_typecheck_wrapper((tag, 2), fdel,
                                            cls=cls, use_closure=use_closure)
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc
        self.reqcls = cls
        self.name = '<generic property>'
        self.objclass_getter = objclass_getter
        self.use_closure = use_closure

    def descr_property_get(self, space, w_obj, w_cls=None):
        """property.__get__(obj[, type]) -> value
        Read the value of the property of the given obj."""
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if (space.is_w(w_obj, space.w_None)
            and not space.is_w(w_cls, space.type(space.w_None))):
            #print self, w_obj, w_cls
            return space.wrap(self)
        else:
            try:
                return self.fget(self, space, w_obj)
            except DescrMismatch, e:
                return w_obj.descr_call_mismatch(
                    space, '__getattribute__',
                    self.reqcls, Arguments(space, [w_obj,
                                                   space.wrap(self.name)]))

    def descr_property_set(self, space, w_obj, w_value):
        """property.__set__(obj, value)
        Change the value of the property of the given obj."""
        fset = self.fset
        if fset is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("readonly attribute"))
        try:
            fset(self, space, w_obj, w_value)
        except DescrMismatch, e:
            w_obj.descr_call_mismatch(
                space, '__setattr__',
                self.reqcls, Arguments(space, [w_obj,
                                               space.wrap(self.name),
                                               w_value]))

    def descr_property_del(self, space, w_obj):
        """property.__delete__(obj)
        Delete the value of the property from the given obj."""
        fdel = self.fdel
        if fdel is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("cannot delete attribute"))
        try:
            fdel(self, space, w_obj)
        except DescrMismatch, e:
            w_obj.descr_call_mismatch(
                space, '__delattr__',
                self.reqcls, Arguments(space, [w_obj,
                                               space.wrap(self.name)]))
    
    def descr_get_objclass(space, property):
        return property.objclass_getter(space)

def interp_attrproperty(name, cls, doc=None):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    return GetSetProperty(fget, cls=cls, doc=doc)

def interp_attrproperty_w(name, cls, doc=None):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, obj):
        w_value = getattr(obj, name)
        if w_value is None:
            return space.w_None
        else:
            return w_value
    
    return GetSetProperty(fget, cls=cls, doc=doc)

GetSetProperty.typedef = TypeDef(
    "getset_descriptor",
    __get__ = interp2app(GetSetProperty.descr_property_get),
    __set__ = interp2app(GetSetProperty.descr_property_set),
    __delete__ = interp2app(GetSetProperty.descr_property_del),
    __name__ = interp_attrproperty('name', cls=GetSetProperty),
    __objclass__ = GetSetProperty(GetSetProperty.descr_get_objclass),
    __doc__ = interp_attrproperty('doc', cls=GetSetProperty),
    )
GetSetProperty.typedef.acceptable_as_base_class = False


class Member(Wrappable):
    """For slots."""
    _immutable_ = True
    def __init__(self, index, name, w_cls):
        self.index = index
        self.name = name
        self.w_cls = w_cls
    
    def typecheck(self, space, w_obj):
        if not space.is_true(space.isinstance(w_obj, self.w_cls)):
            raise operationerrfmt(space.w_TypeError,
                                  "descriptor '%s' for '%s'"
                                  " objects doesn't apply to '%s' object",
                                  self.name,
                                  self.w_cls.name,
                                  space.type(w_obj).getname(space))
    
    def descr_member_get(self, space, w_obj, w_w_cls=None):
        """member.__get__(obj[, type]) -> value
        Read the slot 'member' of the given 'obj'."""
        if space.is_w(w_obj, space.w_None):
            return space.wrap(self)
        else:
            self.typecheck(space, w_obj)
            w_result = w_obj.getslotvalue(self.index)
            if w_result is None:
                raise OperationError(space.w_AttributeError,
                                     space.wrap(self.name)) # XXX better message
            return w_result
    
    def descr_member_set(self, space, w_obj, w_value):
        """member.__set__(obj, value)
        Write into the slot 'member' of the given 'obj'."""
        self.typecheck(space, w_obj)
        w_obj.setslotvalue(self.index, w_value)
    
    def descr_member_del(self, space, w_obj):
        """member.__delete__(obj)
        Delete the value of the slot 'member' from the given 'obj'."""
        self.typecheck(space, w_obj)
        w_oldresult = w_obj.getslotvalue(self.index)
        if w_oldresult is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap(self.name)) # XXX better message
        w_obj.setslotvalue(self.index, None)

Member.typedef = TypeDef(
    "member_descriptor",
    __get__ = interp2app(Member.descr_member_get),
    __set__ = interp2app(Member.descr_member_set),
    __delete__ = interp2app(Member.descr_member_del),
    __name__ = interp_attrproperty('name', cls=Member),
    __objclass__ = interp_attrproperty_w('w_cls', cls=Member),
    )
Member.typedef.acceptable_as_base_class = False

# ____________________________________________________________

def generic_new_descr(W_Type):
    def descr_new(space, w_subtype, __args__):
        self = space.allocate_instance(W_Type, w_subtype)
        W_Type.__init__(self, space)
        return space.wrap(self)
    descr_new = func_with_new_name(descr_new, 'descr_new_%s' % W_Type.__name__)
    return interp2app(descr_new)

# ____________________________________________________________
#
# Definition of the type's descriptors for all the internal types

from pypy.interpreter.eval import Code, Frame
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pyopcode import SuspendedUnroller
from pypy.interpreter.module import Module
from pypy.interpreter.function import Function, Method, StaticMethod
from pypy.interpreter.function import ClassMethod
from pypy.interpreter.function import BuiltinFunction, descr_function_get
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.special import NotImplemented, Ellipsis

def descr_get_dict(space, w_obj):
    w_dict = w_obj.getdict(space)
    if w_dict is None:
        typename = space.type(w_obj).getname(space)
        raise operationerrfmt(space.w_TypeError,
                              "descriptor '__dict__' doesn't apply to"
                              " '%s' objects", typename)
    return w_dict

def descr_set_dict(space, w_obj, w_dict):
    w_obj.setdict(space, w_dict)

def descr_del_dict(space, w_obj): # blame CPython for the existence of this one
    w_obj.setdict(space, space.newdict())

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
    return space.wrap(code.signature().num_argnames())

def fget_co_flags(space, code): # unwrapping through unwrap_spec
    sig = code.signature()
    flags = 0
    if sig.has_vararg(): flags |= CO_VARARGS
    if sig.has_kwarg(): flags |= CO_VARKEYWORDS
    return space.wrap(flags)

def fget_co_consts(space, code): # unwrapping through unwrap_spec
    w_docstring = code.getdocstring(space)
    return space.newtuple([w_docstring])

weakref_descr = GetSetProperty(descr_get_weakref,
                    doc="list of weak references to the object (if defined)")
weakref_descr.name = '__weakref__'

def make_weakref_descr(cls):
    """Make instances of the Wrappable subclass 'cls' weakrefable.
    This returns the '__weakref__' desctriptor to use for the TypeDef.
    Note that if the class also defines a custom '__del__', the
    __del__ should call self.clear_all_weakrefs() before it clears
    the resources used by the object.
    """
    # force the interface into the given cls
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline
    def delweakref(self):
        self._lifeline_ = None
    cls._lifeline_ = None
    cls.getweakref = getweakref
    cls.setweakref = setweakref
    cls.delweakref = delweakref
    return weakref_descr


Code.typedef = TypeDef('internal-code',
    co_name = interp_attrproperty('co_name', cls=Code),
    co_varnames = GetSetProperty(fget_co_varnames, cls=Code),
    co_argcount = GetSetProperty(fget_co_argcount, cls=Code),
    co_flags = GetSetProperty(fget_co_flags, cls=Code),
    co_consts = GetSetProperty(fget_co_consts, cls=Code),
    )
Code.typedef.acceptable_as_base_class = False

BuiltinCode.typedef = TypeDef('builtin-code',
    __reduce__   = interp2app(BuiltinCode.descr__reduce__),
    co_name = interp_attrproperty('co_name', cls=BuiltinCode),
    co_varnames = GetSetProperty(fget_co_varnames, cls=BuiltinCode),
    co_argcount = GetSetProperty(fget_co_argcount, cls=BuiltinCode),
    co_flags = GetSetProperty(fget_co_flags, cls=BuiltinCode),
    co_consts = GetSetProperty(fget_co_consts, cls=BuiltinCode),
    )
BuiltinCode.typedef.acceptable_as_base_class = False


Frame.typedef = TypeDef('internal-frame',
    f_code = GetSetProperty(Frame.fget_code),
    f_locals = GetSetProperty(Frame.fget_getdictscope),
    f_globals = interp_attrproperty_w('w_globals', cls=Frame),
    )
Frame.typedef.acceptable_as_base_class = False

PyCode.typedef = TypeDef('code',
    __new__ = interp2app(PyCode.descr_code__new__.im_func),
    __eq__ = interp2app(PyCode.descr_code__eq__),
    __ne__ = descr_generic_ne,
    __hash__ = interp2app(PyCode.descr_code__hash__),
    __reduce__   = interp2app(PyCode.descr__reduce__),
    __repr__ = interp2app(PyCode.repr),
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
    __weakref__ = make_weakref_descr(PyCode),
    )
PyCode.typedef.acceptable_as_base_class = False

PyFrame.typedef = TypeDef('frame',
    __reduce__   = interp2app(PyFrame.descr__reduce__),
    __setstate__ = interp2app(PyFrame.descr__setstate__),
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
PyFrame.typedef.acceptable_as_base_class = False

Module.typedef = TypeDef("module",
    __new__ = interp2app(Module.descr_module__new__.im_func),
    __init__ = interp2app(Module.descr_module__init__),
    __repr__ = interp2app(Module.descr_module__repr__),
    __reduce__ = interp2app(Module.descr__reduce__),
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
    __new__ = interp2app(Function.descr_function__new__.im_func),
    __call__ = interp2app(Function.descr_function_call,
                          descrmismatch='__call__'),
    __get__ = interp2app(descr_function_get),
    __repr__ = interp2app(Function.descr_function_repr, descrmismatch='__repr__'),
    __reduce__ = interp2app(Function.descr_function__reduce__),
    __setstate__ = interp2app(Function.descr_function__setstate__),
    func_code = getset_func_code,
    func_doc = getset_func_doc,
    func_name = getset_func_name,
    func_dict = getset_func_dict,
    func_defaults = getset_func_defaults,
    func_globals = interp_attrproperty_w('w_func_globals', cls=Function),
    func_closure = GetSetProperty( Function.fget_func_closure ),
    __code__ = getset_func_code,
    __doc__ = getset_func_doc,
    __name__ = getset_func_name,
    __dict__ = getset_func_dict,
    __defaults__ = getset_func_defaults,
    __module__ = getset___module__,
    __weakref__ = make_weakref_descr(Function),
    )
Function.typedef.acceptable_as_base_class = False

Method.typedef = TypeDef(
    "method",
    __new__ = interp2app(Method.descr_method__new__.im_func),
    __call__ = interp2app(Method.descr_method_call),
    __get__ = interp2app(Method.descr_method_get),
    im_func  = interp_attrproperty_w('w_function', cls=Method),
    __func__ = interp_attrproperty_w('w_function', cls=Method),
    im_self  = interp_attrproperty_w('w_instance', cls=Method),
    __self__ = interp_attrproperty_w('w_instance', cls=Method),
    im_class = interp_attrproperty_w('w_class', cls=Method),
    __getattribute__ = interp2app(Method.descr_method_getattribute),
    __eq__ = interp2app(Method.descr_method_eq),
    __ne__ = descr_generic_ne,
    __hash__ = interp2app(Method.descr_method_hash),
    __repr__ = interp2app(Method.descr_method_repr),
    __reduce__ = interp2app(Method.descr_method__reduce__),
    __weakref__ = make_weakref_descr(Method),
    )
Method.typedef.acceptable_as_base_class = False

StaticMethod.typedef = TypeDef("staticmethod",
    __doc__ = """staticmethod(function) -> static method

Convert a function to be a static method.

A static method does not receive an implicit first argument.
To declare a static method, use this idiom:

     class C:
         def f(arg1, arg2, ...): ...
         f = staticmethod(f)

It can be called either on the class (e.g. C.f()) or on an instance
(e.g. C().f()).  The instance is ignored except for its class.""",
    __get__ = interp2app(StaticMethod.descr_staticmethod_get),
    __new__ = interp2app(StaticMethod.descr_staticmethod__new__.im_func),
    __func__= interp_attrproperty_w('w_function', cls=StaticMethod),
    )

ClassMethod.typedef = TypeDef(
    'classmethod',
    __new__ = interp2app(ClassMethod.descr_classmethod__new__.im_func),
    __get__ = interp2app(ClassMethod.descr_classmethod_get),
    __func__= interp_attrproperty_w('w_function', cls=ClassMethod),
    __doc__ = """classmethod(function) -> class method

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
object is passed as the implied first argument.""",
)

def always_none(self, obj):
    return None
BuiltinFunction.typedef = TypeDef("builtin_function",**Function.typedef.rawdict)
BuiltinFunction.typedef.rawdict.update({
    '__new__': interp2app(BuiltinFunction.descr_builtinfunction__new__.im_func),
    '__self__': GetSetProperty(always_none, cls=BuiltinFunction),
    '__repr__': interp2app(BuiltinFunction.descr_function_repr),
    '__doc__': getset_func_doc,
    })
del BuiltinFunction.typedef.rawdict['__get__']
BuiltinFunction.typedef.acceptable_as_base_class = False

PyTraceback.typedef = TypeDef("traceback",
    __reduce__   = interp2app(PyTraceback.descr__reduce__),
    __setstate__ = interp2app(PyTraceback.descr__setstate__),
    tb_frame  = interp_attrproperty('frame', cls=PyTraceback),
    tb_lasti  = interp_attrproperty('lasti', cls=PyTraceback),
    tb_lineno = GetSetProperty(PyTraceback.descr_tb_lineno),
    tb_next   = interp_attrproperty('next', cls=PyTraceback),
    )
PyTraceback.typedef.acceptable_as_base_class = False

GeneratorIterator.typedef = TypeDef("generator",
    __repr__   = interp2app(GeneratorIterator.descr__repr__),
    __reduce__   = interp2app(GeneratorIterator.descr__reduce__),
    next       = interp2app(GeneratorIterator.descr_next,
                            descrmismatch='next'),
    send       = interp2app(GeneratorIterator.descr_send,
                            descrmismatch='send'),
    throw      = interp2app(GeneratorIterator.descr_throw,
                            descrmismatch='throw'),
    close      = interp2app(GeneratorIterator.descr_close,
                            descrmismatch='close'),
    __iter__   = interp2app(GeneratorIterator.descr__iter__,
                            descrmismatch='__iter__'),
    gi_running = interp_attrproperty('running', cls=GeneratorIterator),
    gi_frame   = GetSetProperty(GeneratorIterator.descr_gi_frame),
    gi_code    = GetSetProperty(GeneratorIterator.descr_gi_code),
    __name__   = GetSetProperty(GeneratorIterator.descr__name__),
    __weakref__ = make_weakref_descr(GeneratorIterator),
)
GeneratorIterator.typedef.acceptable_as_base_class = False

Cell.typedef = TypeDef("cell",
    __cmp__      = interp2app(Cell.descr__cmp__),
    __hash__     = None,
    __reduce__   = interp2app(Cell.descr__reduce__),
    __setstate__ = interp2app(Cell.descr__setstate__),
    cell_contents= GetSetProperty(Cell.descr__cell_contents, cls=Cell),
)
Cell.typedef.acceptable_as_base_class = False

Ellipsis.typedef = TypeDef("Ellipsis",
    __repr__   = interp2app(Ellipsis.descr__repr__),
)
Ellipsis.typedef.acceptable_as_base_class = False

NotImplemented.typedef = TypeDef("NotImplemented",
    __repr__   = interp2app(NotImplemented.descr__repr__),
)
NotImplemented.typedef.acceptable_as_base_class = False

SuspendedUnroller.typedef = TypeDef("SuspendedUnroller")
SuspendedUnroller.typedef.acceptable_as_base_class = False
