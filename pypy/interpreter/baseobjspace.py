import sys

from rpython.rlib.cache import Cache
from rpython.tool.uid import HUGEVAL_BYTES
from rpython.rlib import jit, types
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib.objectmodel import (we_are_translated, newlist_hint,
     compute_unique_id, specialize, not_rpython)
from rpython.rlib.signature import signature
from rpython.rlib.rarithmetic import r_uint, SHRT_MIN, SHRT_MAX, \
    INT_MIN, INT_MAX, UINT_MAX, USHRT_MAX
from rpython.rlib.buffer import StringBuffer

from pypy.interpreter.buffer import BufferInterfaceNotFound
from pypy.interpreter.executioncontext import (ExecutionContext, ActionFlag,
    make_finalizer_queue)
from pypy.interpreter.error import OperationError, new_exception_class, oefmt
from pypy.interpreter.argument import Arguments
from pypy.interpreter.miscutils import ThreadLocals, make_weak_value_dictionary


__all__ = ['ObjSpace', 'OperationError', 'W_Root']

unpackiterable_driver = jit.JitDriver(name='unpackiterable',
                                      greens=['tp'],
                                      reds=['items', 'w_iterator'])


class W_Root(object):
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    __slots__ = ('__weakref__',)
    _must_be_light_finalizer_ = True
    user_overridden_class = False

    def getdict(self, space):
        return None

    def getdictvalue(self, space, attr):
        w_dict = self.getdict(space)
        if w_dict is not None:
            return space.finditem_str(w_dict, attr)
        return None

    def setdictvalue(self, space, attr, w_value):
        w_dict = self.getdict(space)
        if w_dict is not None:
            space.setitem_str(w_dict, attr, w_value)
            return True
        return False

    def deldictvalue(self, space, attr):
        w_dict = self.getdict(space)
        if w_dict is not None:
            try:
                space.delitem(w_dict, space.newtext(attr))
                return True
            except OperationError as ex:
                if not ex.match(space, space.w_KeyError):
                    raise
        return False

    def setdict(self, space, w_dict):
        raise oefmt(space.w_TypeError,
                     "attribute '__dict__' of %T objects is not writable",
                     self)

    # to be used directly only by space.type implementations
    def getclass(self, space):
        return space.gettypeobject(self.typedef)

    def setclass(self, space, w_subtype):
        raise oefmt(space.w_TypeError,
                    "__class__ assignment: only for heap types")

    def user_setup(self, space, w_subtype):
        raise NotImplementedError("only for interp-level user subclasses "
                                  "from typedef.py")

    def getname(self, space):
        try:
            return space.unicode_w(space.getattr(self, space.newtext('__name__')))
        except OperationError as e:
            if e.match(space, space.w_TypeError) or e.match(space, space.w_AttributeError):
                return u'?'
            raise

    def getaddrstring(self, space):
        # slowish
        w_id = space.id(self)
        w_4 = space.newint(4)
        w_0x0F = space.newint(0x0F)
        i = 2 * HUGEVAL_BYTES
        addrstring = [' '] * i
        while True:
            n = space.int_w(space.and_(w_id, w_0x0F), allow_conversion=False)
            n += ord('0')
            if n > ord('9'):
                n += (ord('a') - ord('9') - 1)
            i -= 1
            addrstring[i] = chr(n)
            if i == 0:
                break
            w_id = space.rshift(w_id, w_4)
        return ''.join(addrstring)

    def getrepr(self, space, info, moreinfo=u''):
        addrstring = unicode(self.getaddrstring(space))
        return space.newunicode(u"<%s at 0x%s%s>" % (info, addrstring, moreinfo))

    def getslotvalue(self, index):
        raise NotImplementedError

    def setslotvalue(self, index, w_val):
        raise NotImplementedError

    def delslotvalue(self, index):
        raise NotImplementedError

    def descr_call_mismatch(self, space, opname, RequiredClass, args):
        if RequiredClass is None:
            classname = '?'
        else:
            classname = wrappable_class_name(RequiredClass)
        raise oefmt(space.w_TypeError,
                    "'%s' object expected, got '%T' instead", classname, self)

    # used by _weakref implemenation

    def getweakref(self):
        return None

    def setweakref(self, space, weakreflifeline):
        raise oefmt(space.w_TypeError,
                    "cannot create weak reference to '%T' object", self)

    def delweakref(self):
        pass

    def clear_all_weakrefs(self):
        """Ensures that weakrefs (if any) are cleared now.  This is
        called by UserDelAction before the object is finalized further.
        """
        lifeline = self.getweakref()
        if lifeline is not None:
            # Clear all weakrefs to this object before we proceed with
            # the destruction of the object.  We detach the lifeline
            # first: if the code following before_del() calls the
            # app-level, e.g. a user-defined __del__(), and this code
            # tries to use weakrefs again, it won't reuse the broken
            # (already-cleared) weakrefs from this lifeline.
            self.delweakref()
            lifeline.clear_all_weakrefs()

    def _finalize_(self):
        """The RPython-level finalizer.

        By default, it is *not called*.  See self.register_finalizer().
        Be ready to handle the case where the object is only half
        initialized.  Also, in some cases the object might still be
        visible to app-level after _finalize_() is called (e.g. if
        there is a __del__ that resurrects).
        """

    def register_finalizer(self, space):
        """Register a finalizer for this object, so that
        self._finalize_() will be called.  You must call this method at
        most once.  Be ready to handle in _finalize_() the case where
        the object is half-initialized, even if you only call
        self.register_finalizer() at the end of the initialization.
        This is because there are cases where the finalizer is already
        registered before: if the user makes an app-level subclass with
        a __del__.  (In that case only, self.register_finalizer() does
        nothing, because the finalizer is already registered in
        allocate_instance().)
        """
        if self.user_overridden_class and self.getclass(space).hasuserdel:
            # already registered by space.allocate_instance()
            if not we_are_translated():
                assert space.finalizer_queue._already_registered(self)
        else:
            if not we_are_translated():
                # does not make sense if _finalize_ is not overridden
                assert self._finalize_.im_func is not W_Root._finalize_.im_func
            space.finalizer_queue.register_finalizer(self)

    def may_unregister_rpython_finalizer(self, space):
        """Optimization hint only: if there is no user-defined __del__()
        method, pass the hint ``don't call any finalizer'' to rgc.
        """
        if not self.getclass(space).hasuserdel:
            from rpython.rlib import rgc
            rgc.may_ignore_finalizer(self)

    # hooks that the mapdict implementations needs:
    def _get_mapdict_map(self):
        return None
    def _set_mapdict_map(self, map):
        raise NotImplementedError
    def _mapdict_read_storage(self, index):
        raise NotImplementedError
    def _mapdict_write_storage(self, index, value):
        raise NotImplementedError
    def _mapdict_storage_length(self):
        raise NotImplementedError
    def _set_mapdict_storage_and_map(self, storage, map):
        raise NotImplementedError

    # -------------------------------------------------------------------

    def is_w(self, space, w_other):
        return self is w_other

    def immutable_unique_id(self, space):
        return None

    def buffer_w(self, space, flags):
        return self.__buffer_w(space, flags).buffer_w(space, flags)

    def __buffer_w(self, space, flags):
        w_impl = space.lookup(self, '__buffer__')
        if w_impl is not None:
            w_result = space.get_and_call_function(w_impl, self,
                                                   space.newint(flags))
            if space.isinstance_w(w_result, space.w_memoryview):
                return w_result
        raise BufferInterfaceNotFound

    def bytes_w(self, space):
        self._typed_unwrap_error(space, "bytes")

    def unicode_w(self, space):
        self._typed_unwrap_error(space, "string")

    def text_w(self, space):
        self._typed_unwrap_error(space, "string")

    def bytearray_list_of_chars_w(self, space):
        self._typed_unwrap_error(space, "bytearray")

    def int_w(self, space, allow_conversion=True):
        # note that W_IntObject.int_w has a fast path and W_FloatObject.int_w
        # raises w_TypeError
        w_obj = self
        if allow_conversion:
            w_obj = space.int(self)
        return w_obj._int_w(space)

    def _int_w(self, space):
        self._typed_unwrap_error(space, "integer")

    def float_w(self, space, allow_conversion=True):
        w_obj = self
        if allow_conversion:
            w_obj = space.float(self)
        return w_obj._float_w(space)

    def _float_w(self, space):
        self._typed_unwrap_error(space, "float")

    def uint_w(self, space):
        self._typed_unwrap_error(space, "integer")

    def bigint_w(self, space, allow_conversion=True):
        # note that W_IntObject and W_LongObject have fast paths,
        # W_FloatObject.rbigint_w raises w_TypeError raises
        w_obj = self
        if allow_conversion:
            w_obj = space.int(self)
        return w_obj._bigint_w(space)

    def _bigint_w(self, space):
        self._typed_unwrap_error(space, "integer")

    def _typed_unwrap_error(self, space, expected):
        raise oefmt(space.w_TypeError,
                    "expected %s, got %T object", expected, self)

    def int(self, space):
        w_impl = space.lookup(self, '__int__')
        if w_impl is None:
            self._typed_unwrap_error(space, "integer")
        w_result = space.get_and_call_function(w_impl, self)

        if space.is_w(space.type(w_result), space.w_int):
            return w_result
        if space.isinstance_w(w_result, space.w_int):
            tp = space.type(w_result).name
            space.warn(space.newtext(
                "__int__ returned non-int (type %s).  "
                "The ability to return an instance of a strict subclass of int "
                "is deprecated, and may be removed in a future version of "
                "Python." % (tp,)), space.w_DeprecationWarning)
            return w_result
        raise oefmt(space.w_TypeError,
                    "__int__ returned non-int (type '%T')", w_result)

    def ord(self, space):
        raise oefmt(space.w_TypeError,
                    "ord() expected string of length 1, but %T found", self)

    def spacebind(self, space):
        """ Return a version of the object bound to a specific object space
        instance. This is used for objects (like e.g. TypeDefs) that are
        constructed before there is an object space instance. """
        return self

    @not_rpython
    def unwrap(self, space):
        # _____ this code is here to support testing only _____
        return self

    def unpackiterable_int(self, space):
        lst = space.listview_int(self)
        if lst:
            return lst[:]
        return None

    def unpackiterable_float(self, space):
        lst = space.listview_float(self)
        if lst:
            return lst[:]
        return None


class InterpIterable(object):
    def __init__(self, space, w_iterable):
        self.w_iter = space.iter(w_iterable)
        self.space = space

    def __iter__(self):
        return self

    def next(self):
        space = self.space
        try:
            return space.next(self.w_iter)
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            raise StopIteration

class InternalSpaceCache(Cache):
    """A generic cache for an object space.  Arbitrary information can
    be attached to the space by defining a function or class 'f' which
    can be called as 'f(space)'.  Its result is stored in this
    ObjSpaceCache.
    """
    def __init__(self, space):
        Cache.__init__(self)
        self.space = space
    def _build(self, callable):
        return callable(self.space)

class SpaceCache(Cache):
    """A base class for all our concrete caches."""
    def __init__(self, space):
        Cache.__init__(self)
        self.space = space

    def _build(self, key):
        return self.build(key)

    def _ready(self, result):
        return self.ready(result)

    def ready(self, result):
        pass

class DescrMismatch(Exception):
    pass

@specialize.memo()
def wrappable_class_name(Class):
    try:
        return Class.typedef.name
    except AttributeError:
        return 'internal subclass of %s' % (Class.__name__,)

class CannotHaveLock(Exception):
    """Raised by space.allocate_lock() if we're translating."""

# ____________________________________________________________

class ObjSpace(object):
    """Base class for the interpreter-level implementations of object spaces.
    http://pypy.readthedocs.org/en/latest/objspace.html"""

    @not_rpython
    def __init__(self, config=None):
        "Basic initialization of objects."
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.threadlocals = ThreadLocals()
        # set recursion limit
        # sets all the internal descriptors
        if config is None:
            from pypy.config.pypyoption import get_pypy_config
            config = get_pypy_config(translating=False)
        self.config = config

        self.builtin_modules = {}
        self.reloading_modules = {}

        self.interned_strings = make_weak_value_dictionary(self, unicode, W_Root)
        self.actionflag = ActionFlag()    # changed by the signal module
        self.check_signal_action = None   # changed by the signal module
        make_finalizer_queue(W_Root, self)
        self._code_of_sys_exc_info = None

        self._builtin_functions_by_identifier = {'': None}

        # can be overridden to a subclass
        self.initialize()

    def startup(self):
        # To be called before using the space
        self.threadlocals.enter_thread(self)

        # Initialize already imported builtin modules
        from pypy.interpreter.module import Module
        w_modules = self.sys.get('modules')
        for w_modname in self.unpackiterable(
                                self.sys.get('builtin_module_names')):
            try:
                w_mod = self.getitem(w_modules, w_modname)
            except OperationError as e:
                if e.match(self, self.w_KeyError):
                    continue
                raise
            if isinstance(w_mod, Module) and not w_mod.startup_called:
                w_mod.init(self)

    def finish(self):
        self.wait_for_thread_shutdown()
        w_atexit = self.getbuiltinmodule('atexit')
        self.call_method(w_atexit, '_run_exitfuncs')
        self.sys.finalizing = True
        self.sys.flush_std_files(self)
        from pypy.interpreter.module import Module
        for w_mod in self.builtin_modules.values():
            if isinstance(w_mod, Module) and w_mod.startup_called:
                w_mod.shutdown(self)

    def wait_for_thread_shutdown(self):
        """Wait until threading._shutdown() completes, provided the threading
        module was imported in the first place.  The shutdown routine will
        wait until all non-daemon 'threading' threads have completed."""
        if not self.config.translation.thread:
            return

        w_modules = self.sys.get('modules')
        w_mod = self.finditem_str(w_modules, 'threading')
        if w_mod is None:
            return

        try:
            self.call_method(w_mod, "_shutdown")
        except OperationError as e:
            e.write_unraisable(self, "threading._shutdown()")

    def __repr__(self):
        try:
            return self._this_space_repr_
        except AttributeError:
            return self.__class__.__name__

    @not_rpython
    def setbuiltinmodule(self, importname):
        """load a lazy pypy/module and put it into sys.modules"""
        if '.' in importname:
            fullname = importname
            importname = fullname.rsplit('.', 1)[1]
        else:
            fullname = "pypy.module.%s" % importname

        Module = __import__(fullname,
                            None, None, ["Module"]).Module
        if Module.applevel_name is not None:
            name = Module.applevel_name
        else:
            name = importname

        mod = Module(self, self.newtext(name))
        mod.install()

        return name

    def getbuiltinmodule(self, name, force_init=False, reuse=True):
        w_name = self.newtext(name)
        w_modules = self.sys.get('modules')
        if not force_init:
            assert reuse
            try:
                return self.getitem(w_modules, w_name)
            except OperationError as e:
                if not e.match(self, self.w_KeyError):
                    raise

        # If the module is a builtin but not yet imported,
        # retrieve it and initialize it
        try:
            w_mod = self.builtin_modules[name]
        except KeyError:
            raise oefmt(self.w_SystemError,
                        "getbuiltinmodule() called with non-builtin module %s",
                        name)

        # Add the module to sys.modules and initialize the module. The
        # order is important to avoid recursions.
        from pypy.interpreter.module import Module
        if isinstance(w_mod, Module):
            if not reuse and w_mod.startup_called:
                # create a copy of the module.  (see issue1514) eventlet
                # patcher relies on this behaviour.
                w_mod2 = Module(self, w_name)
                self.setitem(w_modules, w_name, w_mod2)
                w_mod.getdict(self)  # unlazy w_initialdict
                self.call_method(w_mod2.getdict(self), 'update',
                                 w_mod.w_initialdict)
                return w_mod2
            self.setitem(w_modules, w_name, w_mod)
            w_mod.init(self)
        else:
            self.setitem(w_modules, w_name, w_mod)
        return w_mod

    @not_rpython
    def get_builtinmodule_to_install(self):
        try:
            return self._builtinmodule_list
        except AttributeError:
            pass

        modules = []

        # You can enable more modules by specifying --usemodules=xxx,yyy
        for name, value in self.config.objspace.usemodules:
            if value and name not in modules:
                modules.append(name)

        if self.config.objspace.extmodules:
            for name in self.config.objspace.extmodules.split(','):
                if name not in modules:
                    modules.append(name)

        self._builtinmodule_list = modules
        return self._builtinmodule_list

    @not_rpython
    def make_builtins(self):
        "only for initializing the space."

        from pypy.module.exceptions import Module
        w_name = self.newtext('__exceptions__')
        self.exceptions_module = Module(self, w_name)
        self.exceptions_module.install()

        from pypy.module.imp import Module
        w_name = self.newtext('_imp')
        mod = Module(self, w_name)
        mod.install()

        from pypy.module.sys import Module
        w_name = self.newtext('sys')
        self.sys = Module(self, w_name)
        self.sys.install()

        from pypy.module.__builtin__ import Module
        w_name = self.newtext('builtins')
        self.builtin = Module(self, w_name)
        w_builtin = self.builtin
        w_builtin.install()
        self.setitem(self.builtin.w_dict, self.newtext('__builtins__'), w_builtin)


        exception_types_w = self.export_builtin_exceptions()

        # initialize with "bootstrap types" from objspace  (e.g. w_None)
        types_w = (self.get_builtin_types().items() +
                   exception_types_w.items())
        for name, w_type in types_w:
            self.setitem(self.builtin.w_dict, self.newtext(name), w_type)

        # install mixed modules
        bootstrap_modules = set(('sys', 'imp', 'builtins', 'exceptions'))
        for mixedname in self.get_builtinmodule_to_install():
            if mixedname not in bootstrap_modules:
                self.install_mixedmodule(mixedname)

        w_builtin_module_names = self.newtuple(
            [self.newtext(name) for name in sorted(self.builtin_modules)])

        # force this value into the dict without unlazyfying everything
        self.setitem(self.sys.w_dict, self.newtext('builtin_module_names'),
                     w_builtin_module_names)

    def get_builtin_types(self):
        """Get a dictionary mapping the names of builtin types to the type
        objects."""
        raise NotImplementedError

    @not_rpython
    def export_builtin_exceptions(self):
        w_dic = self.exceptions_module.getdict(self)
        exc_types_w = {}
        w_iter = self.iter(w_dic)
        while True:
            try:
                w_name = self.next(w_iter)
            except OperationError as e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break
            name = self.text_w(w_name)
            if not name.startswith('__'):
                excname = name
                w_exc = self.getitem(w_dic, w_name)
                exc_types_w[name] = w_exc
                setattr(self, "w_" + excname, w_exc)
        return exc_types_w

    @not_rpython
    def install_mixedmodule(self, mixedname):
        self.setbuiltinmodule(mixedname)

    @not_rpython
    def setup_builtin_modules(self):
        "only for initializing the space."
        if self.config.objspace.usemodules.cpyext:
            # Special-case this to have state.install_dll() called early, which
            # is required to initialise sys on Windows.
            from pypy.module.cpyext.state import State
            self.fromcache(State).build_api()
        self.getbuiltinmodule('sys')
        self.getbuiltinmodule('_imp')
        self.getbuiltinmodule('_frozen_importlib')
        self.getbuiltinmodule('builtins')
        for mod in self.builtin_modules.values():
            mod.setup_after_space_initialization()

    @not_rpython
    def initialize(self):
        """Abstract method that should put some minimal
        content into the w_builtins."""

    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        # Important: the annotator must not see a prebuilt ExecutionContext:
        # you should not see frames while you translate
        # so we make sure that the threadlocals never *have* an
        # ExecutionContext during translation.
        if not we_are_translated():
            if self.config.translating:
                assert self.threadlocals.get_ec() is None, (
                    "threadlocals got an ExecutionContext during translation!")
                try:
                    return self._ec_during_translation
                except AttributeError:
                    ec = self.createexecutioncontext()
                    self._ec_during_translation = ec
                    return ec
            else:
                ec = self.threadlocals.get_ec()
                if ec is None:
                    self.threadlocals.enter_thread(self)
                    ec = self.threadlocals.get_ec()
                return ec
        else:
            # translated case follows.  self.threadlocals is either from
            # 'pypy.interpreter.miscutils' or 'pypy.module.thread.threadlocals'.
            # the result is assumed to be non-null: enter_thread() was called
            # by space.startup().
            ec = self.threadlocals.get_ec()
            assert ec is not None
            return ec

    def _freeze_(self):
        return True

    def createexecutioncontext(self):
        "Factory function for execution contexts."
        return ExecutionContext(self)

    def createcompiler(self):
        "Factory function creating a compiler object."
        try:
            return self.default_compiler
        except AttributeError:
            from pypy.interpreter.pycompiler import PythonAstCompiler
            compiler = PythonAstCompiler(self)
            self.default_compiler = compiler
            return compiler

    def createframe(self, code, w_globals, outer_func=None):
        "Create an empty PyFrame suitable for this code object."
        return self.FrameClass(self, code, w_globals, outer_func)

    def allocate_lock(self):
        """Return an interp-level Lock object if threads are enabled,
        and a dummy object if they are not."""
        from rpython.rlib import rthread
        if not self.config.objspace.usemodules.thread:
            return rthread.dummy_lock
        # hack: we can't have prebuilt locks if we're translating.
        # In this special situation we should just not lock at all
        # (translation is not multithreaded anyway).
        if not we_are_translated() and self.config.translating:
            raise CannotHaveLock()
        try:
            return rthread.allocate_lock()
        except rthread.error:
            raise oefmt(self.w_RuntimeError, "out of resources")

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    def not_(self, w_obj):
        return self.newbool(not self.is_true(w_obj))

    def eq_w(self, w_obj1, w_obj2):
        """Implements equality with the double check 'x is y or x == y'."""
        return self.is_w(w_obj1, w_obj2) or self.is_true(self.eq(w_obj1, w_obj2))

    def is_(self, w_one, w_two):
        return self.newbool(self.is_w(w_one, w_two))

    def is_w(self, w_one, w_two):
        # done by a method call on w_two (and not on w_one, because of the
        # expected programming style where we say "if x is None" or
        # "if x is object").
        assert w_two is not None
        return w_two.is_w(self, w_one)

    def is_none(self, w_obj):
        """ mostly for checking inputargs that have unwrap_spec and
        can accept both w_None and None
        """
        return w_obj is None or self.is_w(w_obj, self.w_None)

    def id(self, w_obj):
        w_result = w_obj.immutable_unique_id(self)
        if w_result is None:
            # in the common case, returns an unsigned value
            w_result = self.newint(r_uint(compute_unique_id(w_obj)))
        return w_result

    def hash_w(self, w_obj):
        """shortcut for space.int_w(space.hash(w_obj))"""
        return self.int_w(self.hash(w_obj))

    def len_w(self, w_obj):
        """shortcut for space.int_w(space.len(w_obj))"""
        return self.int_w(self.len(w_obj))

    def contains_w(self, w_container, w_item):
        """shortcut for space.is_true(space.contains(w_container, w_item))"""
        return self.is_true(self.contains(w_container, w_item))

    def setitem_str(self, w_obj, key, w_value):
        # key is a "text", i.e. a byte string (in python3 it
        # represents a utf-8-encoded unicode)
        return self.setitem(w_obj, self.newtext(key), w_value)

    def finditem_str(self, w_obj, key):
        # key is a "text", i.e. a byte string (in python3 it
        # represents a utf-8-encoded unicode)
        return self.finditem(w_obj, self.newtext(key))

    def finditem(self, w_obj, w_key):
        try:
            return self.getitem(w_obj, w_key)
        except OperationError as e:
            if e.match(self, self.w_KeyError):
                return None
            raise

    def findattr(self, w_object, w_name):
        try:
            return self.getattr(w_object, w_name)
        except OperationError as e:
            # a PyPy extension: let SystemExit and KeyboardInterrupt go through
            if e.async(self):
                raise
            return None

    def wrap_none(self, w_obj):
        if w_obj is None:
            return self.w_None
        return w_obj

    @signature(types.any(), types.bool(), returns=types.instance(W_Root))
    def newbool(self, b):
        if b:
            return self.w_True
        else:
            return self.w_False

    def new_interned_w_str(self, w_u):
        assert isinstance(w_u, W_Root)   # and is not None
        u = self.unicode_w(w_u)
        if not we_are_translated():
            assert type(u) is unicode
        w_u1 = self.interned_strings.get(u)
        if w_u1 is None:
            w_u1 = w_u
            self.interned_strings.set(u, w_u1)
        return w_u1

    def new_interned_str(self, s):
        # Assumes an identifier (utf-8 encoded str)
        # returns a "text" object (ie str in python2 and unicode in python3)
        if not we_are_translated():
            assert type(s) is str
        u = s.decode('utf-8')
        w_s1 = self.interned_strings.get(u)
        if w_s1 is None:
            w_s1 = self.newunicode(u)
            self.interned_strings.set(u, w_s1)
        return w_s1

    def get_interned_str(self, s):
        """Assumes an identifier (utf-8 encoded str).  Returns None if
        the identifier is not interned, or not a valid utf-8 string at all.
        """
        # interface for marshal_impl
        if not we_are_translated():
            assert type(s) is str
        try:
            u = s.decode('utf-8')
        except UnicodeDecodeError:
            return None
        return self.interned_strings.get(u)   # may be None

    @specialize.arg(1)
    def descr_self_interp_w(self, RequiredClass, w_obj):
        if not isinstance(w_obj, RequiredClass):
            raise DescrMismatch()
        return w_obj

    @specialize.arg(1)
    def interp_w(self, RequiredClass, w_obj, can_be_None=False):
        """
        Unwrap w_obj, checking that it is an instance of the required internal
        interpreter class.
        """
        assert RequiredClass is not None
        if can_be_None and self.is_none(w_obj):
            return None
        if not isinstance(w_obj, RequiredClass):   # or obj is None
            raise oefmt(self.w_TypeError,
                        "'%s' object expected, got '%N' instead",
                        wrappable_class_name(RequiredClass),
                        w_obj.getclass(self))
        return w_obj

    def unpackiterable(self, w_iterable, expected_length=-1):
        """Unpack an iterable into a real (interpreter-level) list.

        Raise an OperationError(w_ValueError) if the length is wrong."""
        w_iterator = self.iter(w_iterable)
        if expected_length == -1:
            if self.is_generator(w_iterator):
                # special hack for speed
                lst_w = []
                w_iterator.unpack_into(lst_w)
                return lst_w
            return self._unpackiterable_unknown_length(w_iterator, w_iterable)
        else:
            lst_w = self._unpackiterable_known_length(w_iterator,
                                                      expected_length)
            return lst_w[:]     # make the resulting list resizable

    def iteriterable(self, w_iterable):
        return InterpIterable(self, w_iterable)

    def _unpackiterable_unknown_length(self, w_iterator, w_iterable):
        """Unpack an iterable of unknown length into an interp-level
        list.
        """
        # If we can guess the expected length we can preallocate.
        try:
            items = newlist_hint(self.length_hint(w_iterable, 0))
        except MemoryError:
            items = [] # it might have lied

        tp = self.type(w_iterator)
        while True:
            unpackiterable_driver.jit_merge_point(tp=tp,
                                                  w_iterator=w_iterator,
                                                  items=items)
            try:
                w_item = self.next(w_iterator)
            except OperationError as e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            items.append(w_item)
        #
        return items

    @jit.dont_look_inside
    def _unpackiterable_known_length(self, w_iterator, expected_length):
        # Unpack a known length list, without letting the JIT look inside.
        # Implemented by just calling the @jit.unroll_safe version, but
        # the JIT stopped looking inside already.
        return self._unpackiterable_known_length_jitlook(w_iterator,
                                                         expected_length)

    @jit.unroll_safe
    def _unpackiterable_known_length_jitlook(self, w_iterator,
                                             expected_length):
        items = [None] * expected_length
        idx = 0
        while True:
            try:
                w_item = self.next(w_iterator)
            except OperationError as e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            if idx == expected_length:
                raise oefmt(self.w_ValueError,
                            "too many values to unpack (expected %d)",
                            expected_length)
            items[idx] = w_item
            idx += 1
        if idx < expected_length:
            raise oefmt(self.w_ValueError,
                        "not enough values to unpack (expected %d, got %d)",
                        expected_length, idx)
        return items

    def unpackiterable_unroll(self, w_iterable, expected_length):
        # Like unpackiterable(), but for the cases where we have
        # an expected_length and want to unroll when JITted.
        # Returns a fixed-size list.
        w_iterator = self.iter(w_iterable)
        assert expected_length != -1
        return self._unpackiterable_known_length_jitlook(w_iterator,
                                                         expected_length)


    def unpackiterable_int(self, w_obj):
        """
        Return a RPython list of unwrapped ints out of w_obj. The list is
        guaranteed to be acopy of the actual data contained in w_obj, so you
        can freely modify it. It might return None if not supported.
        """
        return w_obj.unpackiterable_int(self)

    def unpackiterable_float(self, w_obj):
        """
        Same as unpackiterable_int, but for floats.
        """
        return w_obj.unpackiterable_float(self)


    def length_hint(self, w_obj, default):
        """Return the length of an object, consulting its __length_hint__
        method if necessary.
        """
        try:
            return self.len_w(w_obj)
        except OperationError as e:
            if not (e.match(self, self.w_TypeError) or
                    e.match(self, self.w_AttributeError)):
                raise

        w_descr = self.lookup(w_obj, '__length_hint__')
        if w_descr is None:
            return default
        try:
            w_hint = self.get_and_call_function(w_descr, w_obj)
        except OperationError as e:
            if not (e.match(self, self.w_TypeError) or
                    e.match(self, self.w_AttributeError)):
                raise
            return default
        if self.is_w(w_hint, self.w_NotImplemented):
            return default

        hint = self.int_w(w_hint)
        if hint < 0:
            raise oefmt(self.w_ValueError,
                        "__length_hint__() should return >= 0")
        return hint

    def fixedview(self, w_iterable, expected_length=-1):
        """ A fixed list view of w_iterable. Don't modify the result
        """
        return make_sure_not_resized(self.unpackiterable(w_iterable,
                                                         expected_length)[:])

    fixedview_unroll = fixedview

    def listview(self, w_iterable, expected_length=-1):
        """ A non-fixed view of w_iterable. Don't modify the result
        """
        return self.unpackiterable(w_iterable, expected_length)

    def listview_no_unpack(self, w_iterable):
        """ Same as listview() if cheap.  If 'w_iterable' is something like
        a generator, for example, then return None instead.
        May return None anyway.
        """
        return None

    def listview_bytes(self, w_list):
        """ Return a list of unwrapped strings out of a list of strings. If the
        argument is not a list or does not contain only strings, return None.
        May return None anyway.
        """
        return None

    def listview_unicode(self, w_list):
        """ Return a list of unwrapped unicode out of a list of unicode. If the
        argument is not a list or does not contain only unicode, return None.
        May return None anyway.
        """
        return None

    def listview_int(self, w_list):
        """ Return a list of unwrapped int out of a list of int. If the
        argument is not a list or does not contain only int, return None.
        May return None anyway.
        """
        return None

    def listview_float(self, w_list):
        """ Return a list of unwrapped float out of a list of float. If the
        argument is not a list or does not contain only float, return None.
        May return None anyway.
        """
        return None

    def view_as_kwargs(self, w_dict):
        """ if w_dict is a kwargs-dict, return two lists, one of unwrapped
        strings and one of wrapped values. otherwise return (None, None)
        """
        return (None, None)

    def newlist_bytes(self, list_s):
        return self.newlist([self.newbytes(s) for s in list_s])

    def newlist_unicode(self, list_u):
        return self.newlist([self.newunicode(u) for u in list_u])

    def newlist_int(self, list_i):
        return self.newlist([self.newint(i) for i in list_i])

    def newlist_float(self, list_f):
        return self.newlist([self.newfloat(f) for f in list_f])

    def newlist_hint(self, sizehint):
        from pypy.objspace.std.listobject import make_empty_list_with_size
        return make_empty_list_with_size(self, sizehint)

    @jit.unroll_safe
    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        if self.is_w(w_exc_type, w_check_class):
            return True   # fast path
        if self.isinstance_w(w_check_class, self.w_tuple):
            for w_t in self.fixedview(w_check_class):
                if self.exception_match(w_exc_type, w_t):
                    return True
            else:
                return False
        return self.exception_issubclass_w(w_exc_type, w_check_class)

    def call_obj_args(self, w_callable, w_obj, args):
        if not self.config.objspace.disable_call_speedhacks:
            # start of hack for performance
            from pypy.interpreter.function import Function
            if isinstance(w_callable, Function):
                return w_callable.call_obj_args(w_obj, args)
            # end of hack for performance
        return self.call_args(w_callable, args.prepend(w_obj))

    def call(self, w_callable, w_args, w_kwds=None):
        args = Arguments.frompacked(self, w_args, w_kwds)
        return self.call_args(w_callable, args)

    def _try_fetch_pycode(self, w_func):
        from pypy.interpreter.function import Function, Method
        if isinstance(w_func, Method):
            w_func = w_func.w_function
        if isinstance(w_func, Function):
            return w_func.code
        return None

    def call_function(self, w_func, *args_w):
        nargs = len(args_w) # used for pruning funccall versions
        if not self.config.objspace.disable_call_speedhacks and nargs < 5:
            # start of hack for performance
            from pypy.interpreter.function import Function, Method
            if isinstance(w_func, Method):
                if nargs < 4:
                    func = w_func.w_function
                    if isinstance(func, Function):
                        return func.funccall(w_func.w_instance, *args_w)

            if isinstance(w_func, Function):
                return w_func.funccall(*args_w)
            # end of hack for performance

        args = Arguments(self, list(args_w))
        return self.call_args(w_func, args)

    def call_valuestack(self, w_func, nargs, frame, methodcall=False):
        # methodcall is only used for better error messages in argument.py
        from pypy.interpreter.function import Function, Method, is_builtin_code
        if frame.get_is_being_profiled() and is_builtin_code(w_func):
            # XXX: this code is copied&pasted :-( from the slow path below
            # call_valuestack().
            args = frame.make_arguments(nargs)
            return self.call_args_and_c_profile(frame, w_func, args)

        if not self.config.objspace.disable_call_speedhacks:
            # start of hack for performance
            if isinstance(w_func, Method):
                # reuse callable stack place for w_inst
                frame.settopvalue(w_func.w_instance, nargs)
                nargs += 1
                methodcall = True
                w_func = w_func.w_function

            if isinstance(w_func, Function):
                return w_func.funccall_valuestack(
                        nargs, frame, methodcall=methodcall)
            # end of hack for performance

        args = frame.make_arguments(nargs)
        return self.call_args(w_func, args)

    def call_args_and_c_profile(self, frame, w_func, args):
        ec = self.getexecutioncontext()
        ec.c_call_trace(frame, w_func, args)
        try:
            w_res = self.call_args(w_func, args)
        except OperationError:
            ec.c_exception_trace(frame, w_func)
            raise
        ec.c_return_trace(frame, w_func, args)
        return w_res

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.newtext(methname))
        return self.call_function(w_meth, *arg_w)

    def raise_key_error(self, w_key):
        e = self.call_function(self.w_KeyError, w_key)
        raise OperationError(self.w_KeyError, e)

    def lookup(self, w_obj, name):
        w_type = self.type(w_obj)
        w_mro = self.getattr(w_type, self.newtext("__mro__"))
        for w_supertype in self.fixedview(w_mro):
            w_value = w_supertype.getdictvalue(self, name)
            if w_value is not None:
                return w_value
        return None

    def is_generator(self, w_obj):
        from pypy.interpreter.generator import GeneratorIterator
        return isinstance(w_obj, GeneratorIterator)

    def callable(self, w_obj):
        return self.newbool(self.lookup(w_obj, "__call__") is not None)

    def issequence_w(self, w_obj):
        flag = self.type(w_obj).flag_map_or_seq
        if flag == 'M':
            return False
        elif flag == 'S':
            return True
        else:
            return (self.lookup(w_obj, '__getitem__') is not None)

    def ismapping_w(self, w_obj):
        flag = self.type(w_obj).flag_map_or_seq
        if flag == 'M':
            return True
        elif flag == 'S':
            return False
        else:
            return self.lookup(w_obj, '__getitem__') is not None

    # The code below only works
    # for the simple case (new-style instance).
    # These methods are patched with the full logic by the builtins
    # module when it is loaded

    def abstract_issubclass_w(self, w_cls1, w_cls2, allow_override=False):
        # Equivalent to 'issubclass(cls1, cls2)'.
        return self.issubtype_w(w_cls1, w_cls2)

    def abstract_isinstance_w(self, w_obj, w_cls, allow_override=False):
        # Equivalent to 'isinstance(obj, cls)'.
        return self.isinstance_w(w_obj, w_cls)

    def abstract_isclass_w(self, w_obj):
        # Equivalent to 'isinstance(obj, type)'.
        return self.isinstance_w(w_obj, self.w_type)

    def abstract_getclass(self, w_obj):
        # Equivalent to 'obj.__class__'.
        return self.type(w_obj)

    def isabstractmethod_w(self, w_obj):
        try:
            w_result = self.getattr(w_obj, self.newtext("__isabstractmethod__"))
        except OperationError as e:
            if e.match(self, self.w_AttributeError):
                return False
            raise
        return self.is_true(w_result)

    # CPython rules allows subclasses of BaseExceptions to be exceptions.
    # This is slightly less general than the case above, so we prefix
    # it with exception_

    def exception_is_valid_obj_as_class_w(self, w_obj):
        if not self.isinstance_w(w_obj, self.w_type):
            return False
        return self.issubtype_w(w_obj, self.w_BaseException)

    def exception_is_valid_class_w(self, w_cls):
        return self.issubtype_w(w_cls, self.w_BaseException)

    def exception_getclass(self, w_obj):
        return self.type(w_obj)

    def exception_issubclass_w(self, w_cls1, w_cls2):
        return self.issubtype_w(w_cls1, w_cls2)

    @not_rpython
    def new_exception_class(self, *args, **kwargs):
        "convenience method to create excceptions in modules"
        return new_exception_class(self, *args, **kwargs)

    # end of special support code

    @not_rpython
    def eval(self, expression, w_globals, w_locals, hidden_applevel=False):
        "For internal debugging."
        if isinstance(expression, str):
            compiler = self.createcompiler()
            expression = compiler.compile(expression, '?', 'eval', 0,
                                         hidden_applevel=hidden_applevel)
        else:
            raise TypeError('space.eval(): expected a string, code or PyCode object')
        return expression.exec_code(self, w_globals, w_locals)

    @not_rpython
    def exec_(self, statement, w_globals, w_locals, hidden_applevel=False,
              filename=None):
        "For internal debugging."
        if filename is None:
            filename = '?'
        from pypy.interpreter.pycode import PyCode
        if isinstance(statement, str):
            compiler = self.createcompiler()
            statement = compiler.compile(statement, filename, 'exec', 0,
                                         hidden_applevel=hidden_applevel)
        if not isinstance(statement, PyCode):
            raise TypeError('space.exec_(): expected a string, code or PyCode object')
        w_key = self.newtext('__builtins__')
        if not self.contains_w(w_globals, w_key):
            self.setitem(w_globals, w_key, self.builtin)
        return statement.exec_code(self, w_globals, w_locals)

    @specialize.arg(2)
    def appexec(self, posargs_w, source):
        """ return value from executing given source at applevel.
            The source must look like
               '''(x, y):
                       do_stuff...
                       return result
               '''
        """
        w_func = self.fromcache(AppExecCache).getorbuild(source)
        args = Arguments(self, list(posargs_w))
        return self.call_args(w_func, args)

    def _next_or_none(self, w_it):
        try:
            return self.next(w_it)
        except OperationError as e:
            if not e.match(self, self.w_StopIteration):
                raise
            return None

    @specialize.arg(3)
    def compare_by_iteration(self, w_iterable1, w_iterable2, op):
        w_it1 = self.iter(w_iterable1)
        w_it2 = self.iter(w_iterable2)
        while True:
            w_x1 = self._next_or_none(w_it1)
            w_x2 = self._next_or_none(w_it2)
            if w_x1 is None or w_x2 is None:
                if op == 'eq': return self.newbool(w_x1 is w_x2)  # both None
                if op == 'ne': return self.newbool(w_x1 is not w_x2)
                if op == 'lt': return self.newbool(w_x2 is not None)
                if op == 'le': return self.newbool(w_x1 is None)
                if op == 'gt': return self.newbool(w_x1 is not None)
                if op == 'ge': return self.newbool(w_x2 is None)
                assert False, "bad value for op"
            if not self.eq_w(w_x1, w_x2):
                if op == 'eq': return self.w_False
                if op == 'ne': return self.w_True
                if op == 'lt': return self.lt(w_x1, w_x2)
                if op == 'le': return self.le(w_x1, w_x2)
                if op == 'gt': return self.gt(w_x1, w_x2)
                if op == 'ge': return self.ge(w_x1, w_x2)
                assert False, "bad value for op"

    def decode_index(self, w_index_or_slice, seqlength):
        """Helper for custom sequence implementations
             -> (index, 0, 0) or
                (start, stop, step)
        """
        if self.isinstance_w(w_index_or_slice, self.w_slice):
            from pypy.objspace.std.sliceobject import W_SliceObject
            assert isinstance(w_index_or_slice, W_SliceObject)
            start, stop, step = w_index_or_slice.indices3(self, seqlength)
        else:
            start = self.int_w(w_index_or_slice, allow_conversion=False)
            if start < 0:
                start += seqlength
            if not (0 <= start < seqlength):
                raise oefmt(self.w_IndexError, "index out of range")
            stop = 0
            step = 0
        return start, stop, step

    def decode_index4(self, w_index_or_slice, seqlength):
        """Helper for custom sequence implementations
             -> (index, 0, 0, 1) or
                (start, stop, step, slice_length)
        """
        if self.isinstance_w(w_index_or_slice, self.w_slice):
            from pypy.objspace.std.sliceobject import W_SliceObject
            assert isinstance(w_index_or_slice, W_SliceObject)
            start, stop, step, length = w_index_or_slice.indices4(self,
                                                                  seqlength)
        else:
            start = self.int_w(w_index_or_slice, allow_conversion=False)
            if start < 0:
                start += seqlength
            if not (0 <= start < seqlength):
                raise oefmt(self.w_IndexError, "index out of range")
            stop = 0
            step = 0
            length = 1
        return start, stop, step, length

    def getindex_w(self, w_obj, w_exception, objdescr=None):
        """Return w_obj.__index__() as an RPython int.
        If w_exception is None, silently clamp in case of overflow;
        else raise w_exception.
        """
        try:
            w_index = self.index(w_obj)
        except OperationError as err:
            if objdescr is None or not err.match(self, self.w_TypeError):
                raise
            raise oefmt(self.w_TypeError,
                        "%s indices must be integers or slices, not %T",
                        objdescr, w_obj)
        try:
            # allow_conversion=False it's not really necessary because the
            # return type of __index__ is already checked by space.index(),
            # but there is no reason to allow conversions anyway
            index = self.int_w(w_index, allow_conversion=False)
        except OperationError as err:
            if not err.match(self, self.w_OverflowError):
                raise
            if not w_exception:
                # w_index should be a long object, but can't be sure of that
                if self.is_true(self.lt(w_index, self.newint(0))):
                    return -sys.maxint-1
                else:
                    return sys.maxint
            else:
                raise oefmt(w_exception,
                            "cannot fit '%T' into an index-sized integer",
                            w_obj)
        else:
            return index

    def getslice(space, w_obj, w_start, w_stop):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.getitem(w_obj, w_slice)

    def setslice(space, w_obj, w_start, w_stop, w_sequence):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.setitem(w_obj, w_slice, w_sequence)

    def delslice(space, w_obj, w_start, w_stop):
        w_slice = space.newslice(w_start, w_stop, space.w_None)
        return space.delitem(w_obj, w_slice)

    def r_longlong_w(self, w_obj, allow_conversion=True):
        bigint = self.bigint_w(w_obj, allow_conversion)
        try:
            return bigint.tolonglong()
        except OverflowError:
            raise oefmt(self.w_OverflowError, "integer too large")

    def r_ulonglong_w(self, w_obj, allow_conversion=True):
        bigint = self.bigint_w(w_obj, allow_conversion)
        try:
            return bigint.toulonglong()
        except OverflowError:
            raise oefmt(self.w_OverflowError, "integer too large")
        except ValueError:
            raise oefmt(self.w_ValueError,
                        "cannot convert negative integer to unsigned int")

    BUF_SIMPLE   = 0x0000
    BUF_WRITABLE = 0x0001
    BUF_FORMAT   = 0x0004
    BUF_ND       = 0x0008
    BUF_STRIDES  = 0x0010 | BUF_ND
    BUF_C_CONTIGUOUS = 0x0020 | BUF_STRIDES
    BUF_F_CONTIGUOUS = 0x0040 | BUF_STRIDES
    BUF_ANY_CONTIGUOUS = 0x0080 | BUF_STRIDES
    BUF_INDIRECT = 0x0100 | BUF_STRIDES

    BUF_CONTIG_RO = BUF_ND
    BUF_CONTIG    = BUF_ND | BUF_WRITABLE

    BUF_FULL_RO = BUF_INDIRECT | BUF_FORMAT
    BUF_FULL    = BUF_INDIRECT | BUF_FORMAT | BUF_WRITABLE

    def check_buf_flags(self, flags, readonly):
        if readonly and flags & self.BUF_WRITABLE == self.BUF_WRITABLE:
            raise oefmt(self.w_BufferError, "Object is not writable.")

    def buffer_w(self, w_obj, flags):
        # New buffer interface, returns a buffer based on flags (PyObject_GetBuffer)
        try:
            return w_obj.buffer_w(self, flags)
        except BufferInterfaceNotFound:
            raise oefmt(self.w_TypeError,
                        "'%T' does not support the buffer interface", w_obj)

    def readbuf_w(self, w_obj):
        # Old buffer interface, returns a readonly buffer (PyObject_AsReadBuffer)
        try:
            return w_obj.buffer_w(self, self.BUF_SIMPLE).as_readbuf()
        except BufferInterfaceNotFound:
            self._getarg_error("bytes-like object", w_obj)

    def writebuf_w(self, w_obj):
        # Old buffer interface, returns a writeable buffer (PyObject_AsWriteBuffer)
        try:
            return w_obj.buffer_w(self, self.BUF_WRITABLE).as_writebuf()
        except (BufferInterfaceNotFound, OperationError):
            self._getarg_error("read-write bytes-like object", w_obj)

    def charbuf_w(self, w_obj):
        # Old buffer interface, returns a character buffer (PyObject_AsCharBuffer)
        if self.isinstance_w(w_obj, self.w_bytes):  # XXX: is this shortcut useful?
            return w_obj.bytes_w(self)
        else:
            return self.readbuf_w(w_obj).as_str()

    def _getarg_error(self, expected, w_obj):
        if self.is_none(w_obj):
            e = oefmt(self.w_TypeError, "a %s is required, not None", expected)
        else:
            e = oefmt(self.w_TypeError, "a %s is required, not %T", expected, w_obj)
        raise e

    @specialize.arg(1)
    def getarg_w(self, code, w_obj):
        if code == 'z*':
            if self.is_none(w_obj):
                return None
            code = 's*'
        if code == 's*':
            # NOTE: 's*' is almost not used any more inside CPython 3.5.
            # Try not to use it pointlessly: it accepts unicodes, which
            # most API in CPython 3.x no longer do.
            if self.isinstance_w(w_obj, self.w_bytes):
                return StringBuffer(w_obj.bytes_w(self))
            if self.isinstance_w(w_obj, self.w_unicode):
                # NB. CPython forbids surrogates here
                return StringBuffer(w_obj.text_w(self))
            try:
                return w_obj.buffer_w(self, self.BUF_SIMPLE).as_readbuf()
            except BufferInterfaceNotFound:
                self._getarg_error("bytes or buffer", w_obj)
        elif code == 's#':
            # NOTE: 's#' is almost not used any more inside CPython 3.5.
            # Try not to use it pointlessly: it accepts unicodes, which
            # most API in CPython 3.x no longer do.
            if self.isinstance_w(w_obj, self.w_bytes):
                return w_obj.bytes_w(self)
            if self.isinstance_w(w_obj, self.w_unicode):  # NB. CPython forbids
                return w_obj.text_w(self)                 # surrogates here
            try:
                return w_obj.buffer_w(self, self.BUF_SIMPLE).as_str()
            except BufferInterfaceNotFound:
                self._getarg_error("bytes or read-only buffer", w_obj)
        elif code == 'w*':
            return self.writebuf_w(w_obj)
        elif code == 'y*':
            return self.readbuf_w(w_obj)
        elif code == 'y#':
            return self.charbuf_w(w_obj)
        else:
            assert False

    def text_or_none_w(self, w_obj):
        return None if self.is_none(w_obj) else self.text_w(w_obj)

    def bytes_w(self, w_obj):
        """ Takes an application level :py:class:`bytes`
            (on PyPy2 this equals `str`) and returns a rpython byte string.
        """
        return w_obj.bytes_w(self)

    def text_w(self, w_obj):
        """ PyPy2 takes either a :py:class:`str` and returns a
            rpython byte string, or it takes an :py:class:`unicode`
            and uses the systems default encoding to return a rpython
            byte string.

            On PyPy3 it takes a :py:class:`str` and it will return
            an utf-8 encoded rpython string.
        """
        return w_obj.text_w(self)

    @not_rpython    # tests only; should be replaced with bytes_w or text_w
    def str_w(self, w_obj):
        """
        if w_obj is unicode, call text_w() (i.e., return the UTF-8-nosg
        encoded string). Else, call bytes_w().

        We should kill str_w completely and manually substitute it with
        text_w/bytes_w at all call sites.  It remains for now for tests only.
        """
        if self.isinstance_w(w_obj, self.w_unicode):
            return w_obj.text_w(self)
        else:
            return w_obj.bytes_w(self)

    def bytes0_w(self, w_obj):
        "Like bytes_w, but rejects strings with NUL bytes."
        from rpython.rlib import rstring
        result = self.bytes_w(w_obj)
        if '\x00' in result:
            raise oefmt(self.w_ValueError,
                        "argument must be a string without NUL characters")
        return rstring.assert_str0(result)

    def text0_w(self, w_obj):
        "Like text_w, but rejects strings with NUL bytes."
        from rpython.rlib import rstring
        result = self.text_w(w_obj)
        if '\x00' in result:
            raise oefmt(self.w_ValueError,
                        "argument must be a string without NUL characters")
        return rstring.assert_str0(result)

    def fsencode_or_none_w(self, w_obj):
        return None if self.is_none(w_obj) else self.fsencode_w(w_obj)

    def byte_w(self, w_obj):
        """
        Convert an index-like object to an interp-level char

        Used for app-level code like "bytearray(b'abc')[0] = 42".
        """
        value = self.getindex_w(w_obj, None)
        if not 0 <= value < 256:
            # this includes the OverflowError in case the long is too large
            raise oefmt(self.w_ValueError, "byte must be in range(0, 256)")
        return chr(value)

    def int_w(self, w_obj, allow_conversion=True):
        """
        Unwrap an app-level int object into an interpret-level int.

        If allow_conversion==True, w_obj might be of any type which implements
        __int__, *except* floats which are explicitly rejected. This is the
        same logic as CPython's PyArg_ParseTuple. If you want to also allow
        floats, you can call space.int_w(space.int(w_obj)).

        If allow_conversion=False, w_obj needs to be an app-level int or a
        subclass.
        """
        return w_obj.int_w(self, allow_conversion)

    def int(self, w_obj):
        return w_obj.int(self)

    def uint_w(self, w_obj):
        return w_obj.uint_w(self)

    def bigint_w(self, w_obj, allow_conversion=True):
        """
        Like int_w, but return a rlib.rbigint object and call __long__ if
        allow_conversion is True.
        """
        return w_obj.bigint_w(self, allow_conversion)

    def float_w(self, w_obj, allow_conversion=True):
        """
        Like int_w, but return an interp-level float and call __float__ if
        allow_conversion is True.
        """
        return w_obj.float_w(self, allow_conversion)

    def unicode_w(self, w_obj):
        return w_obj.unicode_w(self)

    def unicode0_w(self, w_obj):
        "Like unicode_w, but rejects strings with NUL bytes."
        from rpython.rlib import rstring
        result = w_obj.unicode_w(self)
        if u'\x00' in result:
            raise oefmt(self.w_ValueError,
                        "argument must be a unicode string without NUL "
                        "characters")
        return rstring.assert_str0(result)

    realtext_w = text_w         # Python 2 compatibility
    realunicode_w = unicode_w

    def fsencode(space, w_obj):
        from pypy.interpreter.unicodehelper import fsencode
        return fsencode(space, w_obj)

    def fsdecode(space, w_obj):
        from pypy.interpreter.unicodehelper import fsdecode
        return fsdecode(space, w_obj)

    def fsencode_w(self, w_obj):
        if self.isinstance_w(w_obj, self.w_unicode):
            w_obj = self.fsencode(w_obj)
        return self.bytesbuf0_w(w_obj)

    def bytesbuf0_w(self, w_obj):
        # Like bytes0_w(), but also accept a read-only buffer.
        from rpython.rlib import rstring
        try:
            result = self.bytes_w(w_obj)
        except OperationError as e:
            if not e.match(self, self.w_TypeError):
                raise
            result = self.buffer_w(w_obj, self.BUF_FULL_RO).as_str()
        if '\x00' in result:
            raise oefmt(self.w_ValueError,
                        "argument must be a string without NUL characters")
        return rstring.assert_str0(result)

    def fsdecode_w(self, w_obj):
        if self.isinstance_w(w_obj, self.w_bytes):
            w_obj = self.fsdecode(w_obj)
        return self.unicode0_w(w_obj)

    def bool_w(self, w_obj):
        # Unwraps a bool, also accepting an int for compatibility.
        # For cases where you need to accept bools and ints and nothing
        # else.  Note that saying 'bool' in unwrap_spec() doesn't call
        # this, but the general is_true(),  accepting any object.
        return bool(self.int_w(w_obj))

    def ord(self, w_obj):
        return w_obj.ord(self)

    # This is all interface for gateway.py.
    gateway_int_w = int_w
    gateway_float_w = float_w
    gateway_r_longlong_w = r_longlong_w
    gateway_r_ulonglong_w = r_ulonglong_w

    def gateway_r_uint_w(self, w_obj):
        if self.isinstance_w(w_obj, self.w_float):
            raise oefmt(self.w_TypeError,
                        "integer argument expected, got float")
        return self.uint_w(self.int(w_obj))

    def gateway_nonnegint_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level ValueError if
        # the integer is negative.  Here for gateway.py.
        value = self.gateway_int_w(w_obj)
        if value < 0:
            raise oefmt(self.w_ValueError, "expected a non-negative integer")
        return value

    def c_int_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level OverflowError if
        # the integer does not fit in 32 bits.  Here for gateway.py.
        value = self.gateway_int_w(w_obj)
        if value < INT_MIN or value > INT_MAX:
            raise oefmt(self.w_OverflowError, "expected a 32-bit integer")
        return value

    def c_uint_w(self, w_obj):
        # Like space.gateway_uint_w(), but raises an app-level OverflowError if
        # the integer does not fit in 32 bits.  Here for gateway.py.
        value = self.uint_w(w_obj)
        if value > UINT_MAX:
            raise oefmt(self.w_OverflowError,
                        "expected an unsigned 32-bit integer")
        return value

    def c_nonnegint_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level ValueError if
        # the integer is negative or does not fit in 32 bits.  Here
        # for gateway.py.
        value = self.int_w(w_obj)
        if value < 0:
            raise oefmt(self.w_ValueError, "expected a non-negative integer")
        if value > INT_MAX:
            raise oefmt(self.w_OverflowError, "expected a 32-bit integer")
        return value

    def c_short_w(self, w_obj):
        value = self.int_w(w_obj)
        if value < SHRT_MIN:
            raise oefmt(self.w_OverflowError,
                "signed short integer is less than minimum")
        elif value > SHRT_MAX:
            raise oefmt(self.w_OverflowError,
                "signed short integer is greater than maximum")
        return value

    def c_ushort_w(self, w_obj):
        value = self.int_w(w_obj)
        if value < 0:
            raise oefmt(self.w_OverflowError,
                "can't convert negative value to C unsigned short")
        elif value > USHRT_MAX:
            raise oefmt(self.w_OverflowError,
                "Python int too large for C unsigned short")
        return value

    def c_uid_t_w(self, w_obj):
        # xxx assumes that uid_t and gid_t are a C unsigned int.
        # Equivalent to space.c_uint_w(), with the exception that
        # it also accepts -1 and converts that to UINT_MAX, which
        # is (uid_t)-1.  And values smaller than -1 raise
        # OverflowError, not ValueError.
        try:
            return self.c_uint_w(w_obj)
        except OperationError as e:
            if e.match(self, self.w_ValueError):
                # ValueError: cannot convert negative integer to unsigned
                if self.int_w(w_obj) == -1:
                    return UINT_MAX
                raise oefmt(self.w_OverflowError,
                            "user/group id smaller than minimum (-1)")
            raise

    def truncatedint_w(self, w_obj, allow_conversion=True):
        # Like space.gateway_int_w(), but return the integer truncated
        # instead of raising OverflowError.  For obscure cases only.
        try:
            return self.int_w(w_obj, allow_conversion)
        except OperationError as e:
            if not e.match(self, self.w_OverflowError):
                raise
            from rpython.rlib.rarithmetic import intmask
            return intmask(self.bigint_w(w_obj).uintmask())

    def truncatedlonglong_w(self, w_obj, allow_conversion=True):
        # Like space.gateway_r_longlong_w(), but return the integer truncated
        # instead of raising OverflowError.
        try:
            return self.r_longlong_w(w_obj, allow_conversion)
        except OperationError as e:
            if not e.match(self, self.w_OverflowError):
                raise
            from rpython.rlib.rarithmetic import longlongmask
            return longlongmask(self.bigint_w(w_obj).ulonglongmask())

    def c_filedescriptor_w(self, w_fd):
        # This is only used sometimes in CPython, e.g. for os.fsync() but
        # not os.close().  It's likely designed for 'select'.  It's irregular
        # in the sense that it expects either a real int/long or an object
        # with a fileno(), but not an object with an __int__().
        if not self.isinstance_w(w_fd, self.w_int):
            try:
                w_fileno = self.getattr(w_fd, self.newtext("fileno"))
            except OperationError as e:
                if e.match(self, self.w_AttributeError):
                    raise oefmt(self.w_TypeError,
                                "argument must be an int, or have a fileno() "
                                "method.")
                raise
            w_fd = self.call_function(w_fileno)
            if not self.isinstance_w(w_fd, self.w_int):
                raise oefmt(self.w_TypeError,
                            "fileno() returned a non-integer")
        fd = self.c_int_w(w_fd)  # Can raise w_OverflowError
        if fd < 0:
            raise oefmt(self.w_ValueError,
                "file descriptor cannot be a negative integer (%d)", fd)
        return fd

    def warn(self, w_msg, w_warningcls, stacklevel=2):
        from pypy.module._warnings.interp_warnings import do_warn

        # 'w_warningcls' must a Warning subclass
        if not we_are_translated():
            assert self.issubtype_w(w_warningcls, self.w_Warning)
        do_warn(self, w_msg, w_warningcls, stacklevel - 1)


class AppExecCache(SpaceCache):
    @not_rpython
    def build(cache, source):
        space = cache.space
        # XXX will change once we have our own compiler
        import py
        source = source.lstrip()
        assert source.startswith('('), "incorrect header in:\n%s" % (source,)
        source = py.code.Source("def anonymous%s\n" % source)
        w_glob = space.newdict(module=True)
        space.exec_(str(source), w_glob, w_glob)
        return space.getitem(w_glob, space.newtext('anonymous'))


# Table describing the regular part of the interface of object spaces,
# namely all methods which only take w_ arguments and return a w_ result
# (if any).

ObjSpace.MethodTable = [
# method name # symbol # number of arguments # special method name(s)
    ('is_',             'is',        2, []),
    ('id',              'id',        1, []),
    ('type',            'type',      1, []),
    ('isinstance',      'isinstance', 2, ['__instancecheck__']),
    ('issubtype',       'issubtype', 2, ['__subclasscheck__']),  # not for old-style classes
    ('repr',            'repr',      1, ['__repr__']),
    ('str',             'str',       1, ['__str__']),
    ('format',          'format',    2, ['__format__']),
    ('len',             'len',       1, ['__len__']),
    ('hash',            'hash',      1, ['__hash__']),
    ('getattr',         'getattr',   2, ['__getattribute__']),
    ('setattr',         'setattr',   3, ['__setattr__']),
    ('delattr',         'delattr',   2, ['__delattr__']),
    ('getitem',         'getitem',   2, ['__getitem__']),
    ('setitem',         'setitem',   3, ['__setitem__']),
    ('delitem',         'delitem',   2, ['__delitem__']),
    ('trunc',           'trunc',     1, ['__trunc__']),
    ('pos',             'pos',       1, ['__pos__']),
    ('neg',             'neg',       1, ['__neg__']),
    ('nonzero',         'truth',     1, ['__bool__']),
    ('abs',             'abs',       1, ['__abs__']),
    ('ord',             'ord',       1, []),
    ('invert',          '~',         1, ['__invert__']),
    ('add',             '+',         2, ['__add__', '__radd__']),
    ('sub',             '-',         2, ['__sub__', '__rsub__']),
    ('mul',             '*',         2, ['__mul__', '__rmul__']),
    ('truediv',         '/',         2, ['__truediv__', '__rtruediv__']),
    ('floordiv',        '//',        2, ['__floordiv__', '__rfloordiv__']),
    ('div',             'div',       2, ['__div__', '__rdiv__']),
    ('mod',             '%',         2, ['__mod__', '__rmod__']),
    ('divmod',          'divmod',    2, ['__divmod__', '__rdivmod__']),
    ('pow',             '**',        3, ['__pow__', '__rpow__']),
    ('lshift',          '<<',        2, ['__lshift__', '__rlshift__']),
    ('rshift',          '>>',        2, ['__rshift__', '__rrshift__']),
    ('and_',            '&',         2, ['__and__', '__rand__']),
    ('or_',             '|',         2, ['__or__', '__ror__']),
    ('xor',             '^',         2, ['__xor__', '__rxor__']),
    ('matmul',          '@',         2, ['__matmul__', '__rmatmul__']),
    ('int',             'int',       1, ['__int__']),
    ('index',           'index',     1, ['__index__']),
    ('float',           'float',     1, ['__float__']),
    ('inplace_add',     '+=',        2, ['__iadd__']),
    ('inplace_sub',     '-=',        2, ['__isub__']),
    ('inplace_mul',     '*=',        2, ['__imul__']),
    ('inplace_truediv', '/=',        2, ['__itruediv__']),
    ('inplace_floordiv','//=',       2, ['__ifloordiv__']),
    ('inplace_div',     'div=',      2, ['__idiv__']),
    ('inplace_mod',     '%=',        2, ['__imod__']),
    ('inplace_pow',     '**=',       2, ['__ipow__']),
    ('inplace_lshift',  '<<=',       2, ['__ilshift__']),
    ('inplace_rshift',  '>>=',       2, ['__irshift__']),
    ('inplace_and',     '&=',        2, ['__iand__']),
    ('inplace_or',      '|=',        2, ['__ior__']),
    ('inplace_xor',     '^=',        2, ['__ixor__']),
    ('inplace_matmul',  '@=',        2, ['__imatmul__']),
    ('lt',              '<',         2, ['__lt__', '__gt__']),
    ('le',              '<=',        2, ['__le__', '__ge__']),
    ('eq',              '==',        2, ['__eq__', '__eq__']),
    ('ne',              '!=',        2, ['__ne__', '__ne__']),
    ('gt',              '>',         2, ['__gt__', '__lt__']),
    ('ge',              '>=',        2, ['__ge__', '__le__']),
    ('contains',        'contains',  2, ['__contains__']),
    ('iter',            'iter',      1, ['__iter__']),
    ('next',            'next',      1, ['__next__']),
#    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       3, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
]

ObjSpace.BuiltinModuleTable = [
    'builtins',
    'sys',
]

ObjSpace.ConstantTable = [
    'None',
    'False',
    'True',
    'Ellipsis',
    'NotImplemented',
]

ObjSpace.ExceptionTable = [
    'ArithmeticError',
    'AssertionError',
    'AttributeError',
    'BaseException',
    'BufferError',
    'BytesWarning',
    'BlockingIOError',
    'DeprecationWarning',
    'EOFError',
    'EnvironmentError',
    'Exception',
    'FloatingPointError',
    'FutureWarning',
    'GeneratorExit',
    'IOError',
    'ImportError',
    'ImportWarning',
    'IndentationError',
    'IndexError',
    'KeyError',
    'KeyboardInterrupt',
    'LookupError',
    'MemoryError',
    'NameError',
    'NotImplementedError',
    'OSError',
    'OverflowError',
    'ReferenceError',
    'ResourceWarning',
    'RecursionError',
    'RuntimeError',
    'StopIteration',
    'SyntaxError',
    'SyntaxWarning',
    'SystemError',
    'SystemExit',
    'TabError',
    'TypeError',
    'UnboundLocalError',
    'UnicodeDecodeError',
    'UnicodeEncodeError',
    'UnicodeError',
    'UnicodeTranslateError',
    'UnicodeWarning',
    'ValueError',
    'Warning',
    'ZeroDivisionError',
    'RuntimeWarning',
    'PendingDeprecationWarning',
    'UserWarning',
]

if sys.platform.startswith("win"):
    ObjSpace.ExceptionTable += ['WindowsError']

## Irregular part of the interface:
#
#                                   wrap(x) -> w_x
#                              str_w(w_str) -> str
#              int_w(w_ival or w_long_ival) -> ival
#                       float_w(w_floatval) -> floatval
#             uint_w(w_ival or w_long_ival) -> r_uint_val (unsigned int value)
#             bigint_w(w_ival or w_long_ival) -> rbigint
#                               unwrap(w_x) -> x
#                              is_true(w_x) -> True or False
#                  newtuple([w_1, w_2,...]) -> w_tuple
#                   newlist([w_1, w_2,...]) -> w_list
#                                 newdict() -> empty w_dict
#           newslice(w_start,w_stop,w_step) -> w_slice
#              call_args(w_obj,Arguments()) -> w_result

ObjSpace.IrregularOpTable = [
    'wrap',
    'bytes_w',
    'int_w',
    'float_w',
    'uint_w',
    'bigint_w',
    'unicode_w',
    'unwrap',
    'is_true',
    'is_w',
    'newtuple',
    'newlist',
    'newdict',
    'newslice',
    'call_args',
]
