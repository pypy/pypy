import py

from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import W_Root, DescrMismatch
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (interp2app, BuiltinCode, unwrap_spec,
     WrappedDefault)

from rpython.rlib.jit import promote
from rpython.rlib.objectmodel import compute_identity_hash, specialize
from rpython.rlib.objectmodel import instantiate, not_rpython, try_inline, dont_inline
from rpython.tool.sourcetools import compile2, func_with_new_name
from pypy.objspace.std.util import generic_alias_class_getitem


class TypeDef(object):
    @not_rpython
    def __init__(self, __name, __base=None, __total_ordering__=None,
                 __buffer=None, __confirm_applevel_del__=False,
                 _text_signature_=None, variable_sized=False,
                 __rpython_level_class__=None,
                  **rawdict):
        "initialization-time only"
        self.name = __name
        if __base is None:
            bases = []
        elif isinstance(__base, tuple):
            bases = list(__base)
        else:
            bases = [__base]
        self.bases = bases
        # Used in cpyext to fill tp_as_buffer slots
        assert __buffer in {None, 'read-write', 'read'}, "Unknown value for __buffer"
        for base in bases:
            if __buffer is None:
                __buffer = base.buffer
        self.buffer = __buffer
        self.heaptype = False
        self.hasdict = '__dict__' in rawdict
        # no __del__: use an RPython _finalize_() method and register_finalizer
        if not __confirm_applevel_del__:
            assert '__del__' not in rawdict
        self.weakrefable = '__weakref__' in rawdict
        self.doc = rawdict.get('__doc__', None)
        self.text_signature = _text_signature_
        for base in bases:
            self.hasdict |= base.hasdict
            self.weakrefable |= base.weakrefable
        self.rawdict = {}
        self.acceptable_as_base_class = '__new__' in rawdict
        self.applevel_subclasses_base = None
        self.add_entries(**rawdict)
        assert __total_ordering__ in (None, ), "__total_ordering__ was buggy, mostly unused, and has been removed"
        self.variable_sized = variable_sized
        self.rpy_cls = __rpython_level_class__
        self._install_shortcuts()

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

    def _install_shortcuts(self):
        rawdict = self.rawdict
        # guess the class, if not given explicitly
        rpy_cls = self.rpy_cls
        for key, val in rawdict.iteritems():
            ncls = None
            if isinstance(val, interp2app):
                ncls = val.self_type
                if ncls:
                    if rpy_cls is None:
                        rpy_cls = ncls
                    else:
                        if issubclass(ncls, rpy_cls):
                            rpy_cls = ncls # use most specific class
                        else:
                            assert issubclass(rpy_cls, ncls)
        if rpy_cls is None:
            # safety check: if rpy_cls is unknown, and one of the SHORTCUTS is
            # in rawdict, the shortcut could be wrong (if we have an
            # intermediate class that's not W_Root).
            names = [name for name, shortcut_name, fallback, checkerfunc in SHORTCUTS
                if name in rawdict]
            assert not names
            return
        if 'micronumpy' in rpy_cls.__module__:
            return
        if '_descroperation_shortcuts_installed' in rpy_cls.__dict__:
            return
        rpy_cls._descroperation_shortcuts_installed = True
        for name, shortcut_name, fallback, checkerfunc in SHORTCUTS:
            if name not in rawdict or rawdict[name]._staticdefs:
                if W_Root not in rpy_cls.__bases__:

                    shortcut = getattr(rpy_cls, shortcut_name).im_func
                    if shortcut is not fallback:
                        assert shortcut.source_typedef in self.all_bases(), \
                                "getting a wrong shortcut %s for class %s from some base class that is not W_Root" % (name, rpy_cls)
                continue
            shortcut_func = rawdict[name]._make_descroperation_shortcut(
                    name, rpy_cls, checkerfunc)
            shortcut_func.source_typedef = self
            setattr(rpy_cls, shortcut_name, shortcut_func)

    def all_bases(self):
        for base in self.bases:
            yield base
            for up in base.all_bases():
                yield up



# ____________________________________________________________
#  Hash support

def default_identity_hash(space, w_obj):
    w_unique_id = w_obj.immutable_unique_id(space)
    if w_unique_id is None:     # common case
        return space.newint(compute_identity_hash(w_obj))
    else:
        return space.hash(w_unique_id)

# ____________________________________________________________
#
# For each built-in app-level type Xxx that can be subclassed at
# app-level, the corresponding interp-level W_XxxObject class cannot
# generally represent instances of app-level subclasses of Xxx.  The
# reason is that it is missing a place to store the __dict__, the slots,
# the weakref lifeline, and it typically has no interp-level __del__.
# So we create a few interp-level subclasses of W_XxxObject, which add
# some combination of features. This is done using mapdict.

# Note that nowadays, we need not "a few" but only one subclass.  It
# adds mapdict, which flexibly allows all features.  We handle the
# presence or absence of an app-level '__del__' by calling
# register_finalizer() or not.

@specialize.memo()
@not_rpython
def get_unique_interplevel_subclass(space, cls):
    "initialization-time only"
    assert cls.typedef.acceptable_as_base_class
    try:
        return _unique_subclass_cache[cls]
    except KeyError:
        subcls = _getusercls(cls)
        assert cls not in _unique_subclass_cache
        _unique_subclass_cache[cls] = subcls
        return subcls
_unique_subclass_cache = {}

def _getusercls(cls):
    from rpython.rlib import objectmodel
    from pypy.objspace.std.objectobject import W_ObjectObject
    from pypy.objspace.std.mapdict import (BaseUserClassMapdict,
            MapdictDictSupport, MapdictWeakrefSupport,
            _make_storage_mixin_size_n, MapdictStorageMixin,
            MapdictHPySupport)
    # some subtleties here: We want w_obj.getclass to be a small func
    # set, ie less than 5 different implementations. That way, it can be
    # inlined into its callers. This means we cannot give every single
    # user-defined subclass its own getclass, instead we use the same function
    # for all of them. This has the effect that the call to
    # w_obj._get_mapdict_map() in BaseUserClassMapdict.getclass is an
    # *indirect* call. That's fine, however, we want the object subclasses to
    # work somewhat better than the rest, so W_ObjectObjectUserDictWeakrefable
    # should have a *copy* of getclass. This is all achieved by using
    # _share_methods (which shares functions, does not create copies) instead of
    # import_from_mixin, which *does* copy functions. There is a test for all
    # of this in test_mapdict.py, test_correct_method_sharing
    typedef = cls.typedef
    name = cls.__name__ + "User"
    isobjectsubclass = cls is W_ObjectObject

    if isobjectsubclass:
        base_mixin = _make_storage_mixin_size_n()
    else:
        base_mixin = MapdictStorageMixin
    if not isobjectsubclass:
        shared_methods = [BaseUserClassMapdict]
    else:
        shared_methods = []
    if not typedef.hasdict:
        # the type has no dict, mapdict to provide the dict
        shared_methods.append(MapdictDictSupport)
        name += "Dict"
    if not typedef.weakrefable:
        # the type does not support weakrefs yet, mapdict to provide weakref
        # support
        shared_methods.append(MapdictWeakrefSupport)
        name += "Weakrefable"
    shared_methods.append(MapdictHPySupport)

    class subcls(cls):
        user_overridden_class = True
        objectmodel.import_from_mixin(base_mixin)
        if isobjectsubclass:
            objectmodel.import_from_mixin(BaseUserClassMapdict)

    for _, shortcut_name, meth, _ in SHORTCUTS:
        setattr(subcls, shortcut_name, meth)

    for copycls in shared_methods:
        _share_methods(copycls, subcls)
    subcls.__name__ = name
    return subcls

def _share_methods(copycls, subcls):
    for key, value in copycls.__dict__.items():
        if (not key.startswith('__') or key == '__del__'):
            setattr(subcls, key, value)

# ____________________________________________________________
# descroperation shortcuts

SHORTCUTS = []

def use_special_method_shortcut(name, checkerfunc=None):
    """
    use a shortcut for implementations of the special method 'name' for
    built-in types in the decorated descroperation function. The behaviour for
    builtin types will be equivalent to:

        w_descr = space.lookup(w_obj, name)
        return space.get_and_call_function(w_descr, w_obj)

    but only if the special method name exists in the type. Note that this
    means if the descroperation method contains extra logic after the
    get_and_call_function it will be ignored (which is often safe for built-in
    types).

    checkerfunc is a non-translation only safety: it's called with the space
    and the result of the get_and_call_function call and must return True.
    """
    def wrapper(func):
        @dont_inline
        def shortcut_fallback(self, space, *args_w):
            return func(space, self, *args_w)
        shortcut_fallback.func_name = "shortcut_fallback_%s" % name
        shortcut_name = "shortcut_%s" % name
        SHORTCUTS.append((name, shortcut_name, shortcut_fallback, checkerfunc))
        @try_inline
        def call_shortcut(space, self, *args_w):
            return getattr(self, shortcut_name)(space, *args_w)
        setattr(W_Root, shortcut_name, shortcut_fallback)
        return call_shortcut
    return wrapper


# ____________________________________________________________

@specialize.arg(0)
def make_descr_typecheck_wrapper(tag, func, extraargs=(), cls=None,
                                 use_closure=False):
    if func is None:
        return None
    return _make_descr_typecheck_wrapper(tag, func, extraargs, cls, use_closure)

@specialize.memo()
def _make_descr_typecheck_wrapper(tag, func, extraargs, cls, use_closure):
    from rpython.flowspace.bytecode import cpython_code_signature
    # - if cls is None, the wrapped object is passed to the function
    # - if cls is a class, an unwrapped instance is passed
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
        assert issubclass(cls, W_Root)
        source = """
        def descr_typecheck_%(name)s(closure, space, w_obj, %(extra)s):
            obj = space.descr_self_interp_w(%(cls_name)s, w_obj)
            return %(name)s(%(args)s, %(extra)s)
        """
        miniglobals[cls_name] = cls

    name = func.__name__
    extra = ', '.join(extraargs)
    sig = cpython_code_signature(func.func_code)
    argnames = sig.argnames
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

class GetSetProperty(W_Root):
    _immutable_fields_ = ["fget", "fset", "fdel"]
    w_objclass = None

    @specialize.arg(7)
    def __init__(self, fget, fset=None, fdel=None, doc=None,
                 cls=None, use_closure=False, tag=None, name=None):
        if fget and hasattr(fget, 'im_func'):
            assert not cls or cls is fget.im_class
            cls = fget.im_class
        fget = make_descr_typecheck_wrapper((tag, 0), fget,
                                            cls=cls, use_closure=use_closure)
        fset = make_descr_typecheck_wrapper((tag, 1), fset, ('w_value',),
                                            cls=cls, use_closure=use_closure)
        fdel = make_descr_typecheck_wrapper((tag, 2), fdel,
                                            cls=cls, use_closure=use_closure)
        self._init(fget, fset, fdel, doc, cls, use_closure,
                   name)

    def _init(self, fget, fset, fdel, doc, cls, use_closure,
              name):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc
        self.reqcls = cls
        self.w_qualname = None
        self.use_closure = use_closure
        self.name = name if name is not None else '<generic property>'

    def copy_for_type(self, w_objclass):
        if self.reqcls is None:
            new = instantiate(GetSetProperty)
            new._init(self.fget, self.fset, self.fdel, self.doc, self.reqcls,
                      self.use_closure, self.name)
            new.w_objclass = w_objclass
            return new
        else:
            return self

    @unwrap_spec(w_cls = WrappedDefault(None))
    def descr_property_get(self, space, w_obj, w_cls=None):
        """property.__get__(obj[, type]) -> value
        Read the value of the property of the given obj."""
        # XXX HAAAAAAAAAAAACK (but possibly a good one)
        if (space.is_w(w_obj, space.w_None)
            and not space.is_w(w_cls, space.type(space.w_None))):
            #print self, w_obj, w_cls
            if space.is_w(w_cls, space.w_None):
                raise oefmt(space.w_TypeError, "__get__(None, None) is invalid")
            return self
        else:
            try:
                return self.fget(self, space, w_obj)
            except DescrMismatch:
                return w_obj.descr_call_mismatch(
                    space, '__getattribute__',
                    self.reqcls, Arguments(space, [w_obj,
                                                   space.newtext(self.name)]))

    def readonly_attribute(self, space):   # overwritten in cpyext
        if self.name == '<generic property>':
            raise oefmt(space.w_AttributeError, "readonly attribute")
        else:
            raise oefmt(space.w_AttributeError, "readonly attribute '%s'", self.name)

    def descr_property_set(self, space, w_obj, w_value):
        """property.__set__(obj, value)
        Change the value of the property of the given obj."""
        fset = self.fset
        if fset is None:
            raise self.readonly_attribute(space)
        try:
            fset(self, space, w_obj, w_value)
        except DescrMismatch:
            w_obj.descr_call_mismatch(
                space, '__setattr__',
                self.reqcls, Arguments(space, [w_obj,
                                               space.newtext(self.name),
                                               w_value]))

    def descr_property_del(self, space, w_obj):
        """property.__delete__(obj)
        Delete the value of the property from the given obj."""
        fdel = self.fdel
        if fdel is None:
            raise oefmt(space.w_AttributeError,
                        "can't delete %N.%s", w_obj, self.name)
        try:
            fdel(self, space, w_obj)
        except DescrMismatch:
            w_obj.descr_call_mismatch(
                space, '__delattr__',
                self.reqcls, Arguments(space, [w_obj,
                                               space.newtext(self.name)]))

    def descr_get_objclass(self, space):
        if self.w_objclass is not None:
            return self.w_objclass
        if self.reqcls is not None:
            return space.gettypeobject(self.reqcls.typedef)

    def descr_get_qualname(self, space):
        if self.w_qualname is None:
            self.w_qualname = self._calculate_qualname(space)
        return self.w_qualname

    def _calculate_qualname(self, space):
        if self.reqcls is None:
            type_qualname = '?'
        else:
            w_type = space.gettypeobject(self.reqcls.typedef)
            type_qualname = space.text_w(
                space.getattr(w_type, space.newtext('__qualname__')))
        qualname = "%s.%s" % (type_qualname, self.name)
        return space.newtext(qualname)

        # NB. this is an AttributeError to make inspect.py happy
        raise oefmt(space.w_AttributeError,
                    "generic self has no __objclass__")

    def spacebind(self, space):
        if hasattr(space, '_see_getsetproperty'):
            space._see_getsetproperty(self)      # only for fake/objspace.py
        return self


@not_rpython
def interp_attrproperty(name, cls, doc=None, wrapfn=None):
    "initialization-time only"
    assert wrapfn is not None
    def fget(space, obj):
        return getattr(space, wrapfn)(getattr(obj, name))
    return GetSetProperty(fget, cls=cls, doc=doc)

@not_rpython
def interp_attrproperty_w(name, cls, doc=None):
    "initialization-time only"
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
    __name__ = interp_attrproperty('name', cls=GetSetProperty, wrapfn="newtext_or_none"),
    __qualname__ = GetSetProperty(GetSetProperty.descr_get_qualname),
    __objclass__ = GetSetProperty(GetSetProperty.descr_get_objclass),
    __doc__ = interp_attrproperty('doc', cls=GetSetProperty, wrapfn="newtext_or_none"),
    )
assert not GetSetProperty.typedef.acceptable_as_base_class  # no __new__


class Member(W_Root):
    """For slots."""
    _immutable_ = True

    def __init__(self, index, name, w_cls):
        self.index = index
        self.name = name
        self.w_cls = w_cls

    def typecheck(self, space, w_obj):
        if not space.isinstance_w(w_obj, self.w_cls):
            raise oefmt(space.w_TypeError,
                        "descriptor '%N' for '%N' objects doesn't apply to "
                        "'%T' object", self, self.w_cls, w_obj)

    def descr_member_get(self, space, w_obj, w_cls=None):
        """member.__get__(obj[, type]) -> value
        Read the slot 'member' of the given 'obj'."""
        if space.is_w(w_obj, space.w_None):
            return self
        else:
            self.typecheck(space, w_obj)
            w_result = w_obj.getslotvalue(self.index)
            if w_result is None:
                raise OperationError(space.w_AttributeError,
                                     space.newtext(self.name)) # XXX better message
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
        success = w_obj.delslotvalue(self.index)
        if not success:
            raise OperationError(space.w_AttributeError,
                                 space.newtext(self.name)) # XXX better message

Member.typedef = TypeDef(
    "member_descriptor",
    __get__ = interp2app(Member.descr_member_get),
    __set__ = interp2app(Member.descr_member_set),
    __delete__ = interp2app(Member.descr_member_del),
    __name__ = interp_attrproperty('name', cls=Member, wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_cls', cls=Member),
    )
assert not Member.typedef.acceptable_as_base_class  # no __new__

# ____________________________________________________________

class ClassAttr(W_Root):
    """For class-level attributes that need to be initialized
    with some code.  This code is provided as a callback function
    invoked with the space.
    """
    def __init__(self, function):
        self.function = function

    def spacebind(self, space):
        return self.function(space)

# ____________________________________________________________

def generic_new_descr(W_Type):
    def descr_new(space, w_subtype, __args__):
        self = space.allocate_instance(W_Type, w_subtype)
        W_Type.__init__(self, space)
        return self
    descr_new = func_with_new_name(descr_new, 'descr_new_%s' % W_Type.__name__)
    return interp2app(descr_new)

# ____________________________________________________________
#
# Definition of the type's descriptors for all the internal types

from pypy.interpreter.eval import Code
from pypy.interpreter.pycode import PyCode, CO_VARARGS, CO_VARKEYWORDS, W_LineIterator
from pypy.interpreter.pyframe import PyFrame
from pypy.interpreter.pyopcode import SApplicationException
from pypy.interpreter.module import Module
from pypy.interpreter.function import (Function, Method, StaticMethod,
    ClassMethod, BuiltinFunction, descr_function_get)
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.nestedscope import Cell, descr_new_cell
from pypy.interpreter.special import NotImplemented, Ellipsis


def descr_get_dict(space, w_obj):
    w_dict = w_obj.getdict(space)
    if w_dict is None:
        raise oefmt(space.w_TypeError,
                    "descriptor '__dict__' doesn't apply to '%T' objects",
                    w_obj)
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

dict_descr = GetSetProperty(descr_get_dict, descr_set_dict, descr_del_dict,
                            doc="dictionary for instance variables (if defined)")
dict_descr.name = '__dict__'


def generic_ne(space, w_obj1, w_obj2):
    if space.eq_w(w_obj1, w_obj2):
        return space.w_False
    else:
        return space.w_True
descr_generic_ne = interp2app(generic_ne)

# co_xxx interface emulation for built-in code objects
def fget_co_varnames(space, code): # unwrapping through unwrap_spec
    return space.newtuple([space.newtext(name) for name in code.getvarnames()])

def fget_co_argcount(space, code): # unwrapping through unwrap_spec
    return space.newint(code.signature().num_argnames())

def fget_co_posonlyargcount(space, code): # unwrapping through unwrap_spec
    return space.newint(code.signature().num_posonlyargnames())

def fget_co_kwonlyargcount(space, code): # unwrapping through unwrap_spec
    return space.newint(code.signature().num_kwonlyargnames())

def fget_zero(space, code):
    return space.newint(0)

def fget_co_flags(space, code): # unwrapping through unwrap_spec
    sig = code.signature()
    flags = 0
    if sig.has_vararg():
        flags |= CO_VARARGS
    if sig.has_kwarg():
        flags |= CO_VARKEYWORDS
    return space.newint(flags)

def fget_co_consts(space, code): # unwrapping through unwrap_spec
    w_docstring = code.getdocstring(space)
    return space.newtuple([w_docstring])

weakref_descr = GetSetProperty(descr_get_weakref,
                    doc="list of weak references to the object (if defined)")
weakref_descr.name = '__weakref__'

def make_weakref_descr(cls):
    """Make instances of the W_Root subclass 'cls' weakrefable.
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
    co_name = interp_attrproperty('co_name', cls=Code, wrapfn="newtext_or_none"),
    co_varnames = GetSetProperty(fget_co_varnames, cls=Code),
    co_argcount = GetSetProperty(fget_co_argcount, cls=Code),
    co_posonlyargcount = GetSetProperty(fget_zero, cls=Code),
    co_kwonlyargcount = GetSetProperty(fget_zero, cls=Code),
    co_flags = GetSetProperty(fget_co_flags, cls=Code),
    co_consts = GetSetProperty(fget_co_consts, cls=Code),
    )
assert not Code.typedef.acceptable_as_base_class  # no __new__

BuiltinCode.typedef = TypeDef('builtin-code',
    __reduce__   = interp2app(BuiltinCode.descr__reduce__),
    co_name = interp_attrproperty('co_name', cls=BuiltinCode, wrapfn="newtext_or_none"),
    co_varnames = GetSetProperty(fget_co_varnames, cls=BuiltinCode),
    co_argcount = GetSetProperty(fget_co_argcount, cls=BuiltinCode),
    co_posonlyargcount = GetSetProperty(fget_co_posonlyargcount, cls=BuiltinCode),
    co_kwonlyargcount = GetSetProperty(fget_co_kwonlyargcount, cls=BuiltinCode),
    co_flags = GetSetProperty(fget_co_flags, cls=BuiltinCode),
    co_consts = GetSetProperty(fget_co_consts, cls=BuiltinCode),
    )
assert not BuiltinCode.typedef.acceptable_as_base_class  # no __new__


PyCode.typedef = TypeDef('code',
    __new__ = interp2app(PyCode.descr_code__new__.im_func),
    __eq__ = interp2app(PyCode.descr_code__eq__),
    __ne__ = interp2app(PyCode.descr_code__ne__),
    __hash__ = interp2app(PyCode.descr_code__hash__),
    __reduce__ = interp2app(PyCode.descr__reduce__),
    __repr__ = interp2app(PyCode.repr),
    co_argcount = interp_attrproperty('co_argcount', cls=PyCode, wrapfn="newint"),
    co_posonlyargcount = interp_attrproperty('co_posonlyargcount', cls=PyCode, wrapfn="newint"),
    co_kwonlyargcount = interp_attrproperty('co_kwonlyargcount', cls=PyCode, wrapfn="newint"),
    co_nlocals = interp_attrproperty('co_nlocals', cls=PyCode, wrapfn="newint"),
    co_stacksize = interp_attrproperty('co_stacksize', cls=PyCode, wrapfn="newint"),
    co_flags = interp_attrproperty('co_flags', cls=PyCode, wrapfn="newint"),
    co_code = interp_attrproperty('co_code', cls=PyCode, wrapfn="newbytes"),
    co_consts = GetSetProperty(PyCode.fget_co_consts),
    co_names = GetSetProperty(PyCode.fget_co_names),
    co_varnames = GetSetProperty(PyCode.fget_co_varnames),
    co_freevars = GetSetProperty(PyCode.fget_co_freevars),
    co_cellvars = GetSetProperty(PyCode.fget_co_cellvars),
    co_filename = interp_attrproperty_w('w_filename', cls=PyCode),
    co_name = interp_attrproperty('co_name', cls=PyCode, wrapfn="newtext"),
    co_firstlineno = interp_attrproperty('co_firstlineno', cls=PyCode, wrapfn="newint"),
    co_lnotab = interp_attrproperty('co_lnotab', cls=PyCode, wrapfn="newbytes"),
    co_lines = interp2app(PyCode.co_lines),
    replace = interp2app(PyCode.descr_replace),
    __weakref__ = make_weakref_descr(PyCode),
    )
PyCode.typedef.acceptable_as_base_class = False

W_LineIterator.typedef = TypeDef('line_iterator',
    __iter__ = interp2app(W_LineIterator.descr_iter),
    __next__ = interp2app(W_LineIterator.descr_next),
)
W_LineIterator.typedef.acceptable_as_base_class = False


PyFrame.typedef = TypeDef('frame',
    #__reduce__ = interp2app(PyFrame.descr__reduce__),  --- logic not updated
    #__setstate__ = interp2app(PyFrame.descr__setstate__),
    clear = interp2app(PyFrame.descr_clear),
    f_builtins = GetSetProperty(PyFrame.fget_f_builtins),
    f_lineno = GetSetProperty(PyFrame.fget_f_lineno, PyFrame.fset_f_lineno),
    f_back = GetSetProperty(PyFrame.fget_f_back),
    f_lasti = GetSetProperty(PyFrame.fget_f_lasti),
    f_trace = GetSetProperty(PyFrame.fget_f_trace, PyFrame.fset_f_trace,
                             PyFrame.fdel_f_trace),
    f_trace_lines = GetSetProperty(PyFrame.fget_f_trace_lines, PyFrame.fset_f_trace_lines),
    f_trace_opcodes = GetSetProperty(PyFrame.fget_f_trace_opcodes, PyFrame.fset_f_trace_opcodes),
    f_code = GetSetProperty(PyFrame.fget_code),
    f_locals = GetSetProperty(PyFrame.fget_getdictscope),
    f_globals = GetSetProperty(PyFrame.fget_w_globals),
    __repr__ = interp2app(PyFrame.descr_repr),
)
assert not PyFrame.typedef.acceptable_as_base_class  # no __new__

Module.typedef = TypeDef("module",
    __new__ = interp2app(Module.descr_module__new__.im_func),
    __init__ = interp2app(Module.descr_module__init__),
    __repr__ = interp2app(Module.descr_module__repr__),
    __getattribute__=interp2app(Module.descr_getattribute),
    __dir__ = interp2app(Module.descr_module__dir__),
    __reduce__ = interp2app(Module.descr__reduce__),
    __dict__ = GetSetProperty(descr_get_dict, cls=Module), # module dictionaries are readonly attributes
    __doc__ = 'module(name[, doc])\n\nCreate a module object.\nThe name must be a string; the optional doc argument can have any type.',
    __weakref__ = make_weakref_descr(Module),
    )

getset_func_doc = GetSetProperty(Function.fget_func_doc,
                                 Function.fset_func_doc,
                                 Function.fdel_func_doc,
                                )

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
getset_func_kwdefaults = GetSetProperty(Function.fget_func_kwdefaults,
                                        Function.fset_func_kwdefaults,
                                        Function.fdel_func_kwdefaults)
getset_func_code = GetSetProperty(Function.fget_func_code,
                                  Function.fset_func_code)
getset_func_name = GetSetProperty(Function.fget_func_name,
                                  Function.fset_func_name)
getset_func_qualname = GetSetProperty(Function.fget_func_qualname,
                                      Function.fset_func_qualname)
getset_func_annotations = GetSetProperty(Function.fget_func_annotations,
                                        Function.fset_func_annotations,
                                        Function.fdel_func_annotations)

getset_func_dict = GetSetProperty(descr_get_dict, descr_set_dict, cls=Function)

Function.typedef = TypeDef("function",
    __new__ = interp2app(Function.descr_function__new__.im_func),
    __call__ = interp2app(Function.descr_function_call,
                          descrmismatch='__call__'),
    __get__ = interp2app(descr_function_get),
    __repr__ = interp2app(Function.descr_function_repr, descrmismatch='__repr__'),
    #__reduce__ = interp2app(Function.descr_function__reduce__),
    #__setstate__ = interp2app(Function.descr_function__setstate__),
    __code__ = getset_func_code,
    __doc__ = getset_func_doc,
    __name__ = getset_func_name,
    __qualname__ = getset_func_qualname,
    __dict__ = getset_func_dict,
    __defaults__ = getset_func_defaults,
    __defaults_count__ = GetSetProperty(Function.fget_defaults_count),
    __kwdefaults__ = getset_func_kwdefaults,
    __annotations__ = getset_func_annotations,
    __globals__ = interp_attrproperty_w('w_func_globals', cls=Function),
    __closure__ = GetSetProperty(Function.fget_func_closure),
    __module__ = getset___module__,
    __weakref__ = make_weakref_descr(Function),
)
Function.typedef.acceptable_as_base_class = False

Method.typedef = TypeDef(
    "method",
    __doc__ = """instancemethod(function, instance, class)

Create an instance method object.""",
    __new__ = interp2app(Method.descr_method__new__.im_func),
    __call__ = interp2app(Method.descr_method_call),
    __get__ = interp2app(Method.descr_method_get),
    __func__ = interp_attrproperty_w('w_function', cls=Method),
    __self__ = interp_attrproperty_w('w_instance', cls=Method),
    __getattribute__ = interp2app(Method.descr_method_getattribute),
    __eq__ = interp2app(Method.descr_method_eq),
    __ne__ = interp2app(Method.descr_method_ne),
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
    __init__=interp2app(StaticMethod.descr_init),
    __call__=interp2app(StaticMethod.descr_call),
    __func__= interp_attrproperty_w('w_function', cls=StaticMethod),
    __wrapped__= interp_attrproperty_w('w_function', cls=StaticMethod),
    __isabstractmethod__ = GetSetProperty(StaticMethod.descr_isabstract),
    __dict__ = GetSetProperty(descr_get_dict, descr_set_dict,
                              cls=StaticMethod),
    __reduce_ex__ = interp2app(StaticMethod.descr_reduce_ex),
    )

ClassMethod.typedef = TypeDef(
    'classmethod',
    __new__=interp2app(ClassMethod.descr_classmethod__new__.im_func),
    __init__=interp2app(ClassMethod.descr_init),
    __get__=interp2app(ClassMethod.descr_classmethod_get),
    __call__=interp2app(ClassMethod.descr_call),
    __func__=interp_attrproperty_w('w_function', cls=ClassMethod),
    __wrapped__=interp_attrproperty_w('w_function', cls=ClassMethod),
    __isabstractmethod__=GetSetProperty(ClassMethod.descr_isabstract),
    __dict__=GetSetProperty(descr_get_dict, descr_set_dict, cls=ClassMethod),
    __reduce_ex__ = interp2app(ClassMethod.descr_reduce_ex),
    __doc__="""classmethod(function) -> class method

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
BuiltinFunction.typedef = TypeDef("builtin_function", **Function.typedef.rawdict)
BuiltinFunction.typedef.rawdict.update({
    '__new__': interp2app(BuiltinFunction.descr_builtinfunction__new__.im_func),
    '__self__': GetSetProperty(always_none, cls=BuiltinFunction),
    '__repr__': interp2app(BuiltinFunction.descr_function_repr),
    '__doc__': getset_func_doc,
    '__reduce__': interp2app(BuiltinFunction.descr__reduce__),
    })
del BuiltinFunction.typedef.rawdict['__get__']
BuiltinFunction.typedef.acceptable_as_base_class = False

PyTraceback.typedef = TypeDef("traceback",
    __reduce__ = interp2app(PyTraceback.descr__reduce__),
    __new__ = interp2app(PyTraceback.descr_new),
    __setstate__ = interp2app(PyTraceback.descr__setstate__),
    __dir__ = interp2app(PyTraceback.descr__dir__),
    tb_frame = interp_attrproperty_w('frame', cls=PyTraceback),
    tb_lasti = GetSetProperty(PyTraceback.descr_get_tb_lasti, PyTraceback.descr_set_tb_lasti),
    tb_lineno = GetSetProperty(PyTraceback.descr_get_tb_lineno, PyTraceback.descr_set_tb_lineno),
    tb_next = GetSetProperty(PyTraceback.descr_get_next, PyTraceback.descr_set_next),
    )
PyTraceback.typedef.acceptable_as_base_class = False


Cell.typedef = TypeDef("cell",
    __new__      = interp2app(descr_new_cell),
    __eq__       = interp2app(Cell.descr_eq),
    __ne__       = interp2app(Cell.descr_ne),
    __lt__       = interp2app(Cell.descr_lt),
    __gt__       = interp2app(Cell.descr_gt),
    __le__       = interp2app(Cell.descr_le),
    __ge__       = interp2app(Cell.descr_ge),
    __hash__     = None,
    __reduce__   = interp2app(Cell.descr__reduce__),
    __repr__     = interp2app(Cell.descr__repr__),
    __setstate__ = interp2app(Cell.descr__setstate__),
    cell_contents= GetSetProperty(
        Cell.descr__cell_contents,
        Cell.descr_set_cell_contents,
        Cell.descr_del_cell_contents,
        cls=Cell),

)
Cell.typedef.acceptable_as_base_class = False

Ellipsis.typedef = TypeDef("ellipsis",
    __new__ = interp2app(Ellipsis.descr_new_ellipsis),
    __repr__ = interp2app(Ellipsis.descr__repr__),
    __reduce__ = interp2app(Ellipsis.descr__reduce__),
)
Ellipsis.typedef.acceptable_as_base_class = False

NotImplemented.typedef = TypeDef("NotImplementedType",
    __new__ = interp2app(NotImplemented.descr_new_notimplemented),
    __repr__ = interp2app(NotImplemented.descr__repr__),
    __reduce__ = interp2app(NotImplemented.descr__reduce__),
    __bool__ = interp2app(NotImplemented.descr_bool),
)
NotImplemented.typedef.acceptable_as_base_class = False

SApplicationException.typedef = TypeDef("SApplicationException")
SApplicationException.typedef.acceptable_as_base_class = False

## W_OperationError.typedef = TypeDef("OperationError",
##     __reduce__ = interp2app(W_OperationError.descr_reduce),
##     __setstate__ = interp2app(W_OperationError.descr_setstate),
## )
## W_OperationError.typedef.acceptable_as_base_class = False
