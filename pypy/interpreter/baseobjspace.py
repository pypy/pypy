import itertools
import pypy
from pypy.interpreter.executioncontext import ExecutionContext, ActionFlag
from pypy.interpreter.executioncontext import UserDelAction, FrameTraceAction
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.error import new_exception_class
from pypy.interpreter.argument import Arguments
from pypy.interpreter.miscutils import ThreadLocals
from pypy.tool.cache import Cache
from pypy.tool.uid import HUGEVAL_BYTES
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import make_sure_not_resized
from pypy.rlib.timer import DummyTimer, Timer
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib import jit
from pypy.tool.sourcetools import func_with_new_name
import os, sys, py

__all__ = ['ObjSpace', 'OperationError', 'Wrappable', 'W_Root']

UINT_MAX_32_BITS = r_uint(4294967295)


class W_Root(object):
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    __slots__ = ()
    _settled_ = True
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

    def deldictvalue(self, space, w_name):
        w_dict = self.getdict(space)
        if w_dict is not None:
            try:
                space.delitem(w_dict, w_name)
                return True
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
        return False

    def setdict(self, space, w_dict):
        typename = space.type(self).getname(space)
        raise operationerrfmt(space.w_TypeError,
                              "attribute '__dict__' of %s objects "
                              "is not writable", typename)

    # to be used directly only by space.type implementations
    def getclass(self, space):
        return space.gettypeobject(self.typedef)

    def setclass(self, space, w_subtype):
        raise OperationError(space.w_TypeError,
                             space.wrap("__class__ assignment: only for heap types"))

    def user_setup(self, space, w_subtype):
        raise NotImplementedError("only for interp-level user subclasses "
                                  "from typedef.py")

    def getname(self, space, default='?'):
        try:
            return space.str_w(space.getattr(self, space.wrap('__name__')))
        except OperationError, e:
            if e.match(space, space.w_TypeError) or e.match(space, space.w_AttributeError):
                return default
            raise

    def getaddrstring(self, space):
        # XXX slowish
        w_id = space.id(self)
        w_4 = space.wrap(4)
        w_0x0F = space.wrap(0x0F)
        i = 2 * HUGEVAL_BYTES
        addrstring = [' '] * i
        while True:
            n = space.int_w(space.and_(w_id, w_0x0F))
            n += ord('0')
            if n > ord('9'):
                n += (ord('a') - ord('9') - 1)
            i -= 1
            addrstring[i] = chr(n)
            if i == 0:
                break
            w_id = space.rshift(w_id, w_4)
        return ''.join(addrstring)

    def getrepr(self, space, info, moreinfo=''):
        addrstring = self.getaddrstring(space)
        return space.wrap("<%s at 0x%s%s>" % (info, addrstring,
                                              moreinfo))

    def getslotvalue(self, index):
        raise NotImplementedError

    def setslotvalue(self, index, w_val):
        raise NotImplementedError

    def descr_call_mismatch(self, space, opname, RequiredClass, args):
        if RequiredClass is None:
            classname = '?'
        else:
            classname = wrappable_class_name(RequiredClass)
        msg = "'%s' object expected, got '%s' instead"
        raise operationerrfmt(space.w_TypeError, msg,
            classname, self.getclass(space).getname(space))

    # used by _weakref implemenation

    def getweakref(self):
        return None

    def setweakref(self, space, weakreflifeline):
        typename = space.type(self).getname(space)
        raise operationerrfmt(space.w_TypeError,
            "cannot create weak reference to '%s' object", typename)

    def clear_all_weakrefs(self):
        """Call this at the beginning of interp-level __del__() methods
        in subclasses.  It ensures that weakrefs (if any) are cleared
        before the object is further destroyed.
        """
        lifeline = self.getweakref()
        if lifeline is not None:
            # Clear all weakrefs to this object before we proceed with
            # the destruction of the object.  We detach the lifeline
            # first: if the code following before_del() calls the
            # app-level, e.g. a user-defined __del__(), and this code
            # tries to use weakrefs again, it won't reuse the broken
            # (already-cleared) weakrefs from this lifeline.
            self.setweakref(lifeline.space, None)
            lifeline.clear_all_weakrefs()

    __already_enqueued_for_destruction = False

    def _enqueue_for_destruction(self, space, call_user_del=True):
        """Put the object in the destructor queue of the space.
        At a later, safe point in time, UserDelAction will use
        space.userdel() to call the object's app-level __del__ method.
        """
        # this function always resurect the object, so when
        # running on top of CPython we must manually ensure that
        # we enqueue it only once
        if not we_are_translated():
            if self.__already_enqueued_for_destruction:
                return
            self.__already_enqueued_for_destruction = True
        self.clear_all_weakrefs()
        if call_user_del:
            space.user_del_action.register_dying_object(self)

    def _call_builtin_destructor(self):
        pass     # method overridden in typedef.py

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


class Wrappable(W_Root):
    """A subclass of Wrappable is an internal, interpreter-level class
    that can nevertheless be exposed at application-level by space.wrap()."""
    __slots__ = ()
    _settled_ = True

    def __spacebind__(self, space):
        return self

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
        val = self.space.enter_cache_building_mode()
        try:
            return self.build(key)
        finally:
            self.space.leave_cache_building_mode(val)
    def _ready(self, result):
        val = self.space.enter_cache_building_mode()
        try:
            return self.ready(result)
        finally:
            self.space.leave_cache_building_mode(val)
    def ready(self, result):
        pass

class DescrMismatch(Exception):
    pass

def wrappable_class_name(Class):
    try:
        return Class.typedef.name
    except AttributeError:
        return 'internal subclass of %s' % (Class.__name__,)
wrappable_class_name._annspecialcase_ = 'specialize:memo'

# ____________________________________________________________

class ObjSpace(object):
    """Base class for the interpreter-level implementations of object spaces.
    http://codespeak.net/pypy/dist/pypy/doc/objspace.html"""

    full_exceptions = True  # full support for exceptions (normalization & more)

    def __init__(self, config=None):
        "NOT_RPYTHON: Basic initialization of objects."
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

        # import extra modules for side-effects
        import pypy.interpreter.nestedscope     # register *_DEREF bytecodes

        self.interned_strings = {}
        self.actionflag = ActionFlag()    # changed by the signal module
        self.check_signal_action = None   # changed by the signal module
        self.user_del_action = UserDelAction(self)
        self.frame_trace_action = FrameTraceAction(self)

        from pypy.interpreter.pycode import cpython_magic, default_magic
        self.our_magic = default_magic
        self.host_magic = cpython_magic
        # can be overridden to a subclass

        if self.config.objspace.logbytecodes:
            self.bytecodecounts = [0] * 256
            self.bytecodetransitioncount = {}

        if self.config.objspace.timing:
            self.timer = Timer()
        else:
            self.timer = DummyTimer()

        self.initialize()

    def startup(self):
        # To be called before using the space

        # Initialize already imported builtin modules
        from pypy.interpreter.module import Module
        w_modules = self.sys.get('modules')
        for w_modname in self.unpackiterable(
                                self.sys.get('builtin_module_names')):
            try:
                w_mod = self.getitem(w_modules, w_modname)
            except OperationError, e:
                if e.match(self, self.w_KeyError):
                    continue
                raise
            modname = self.str_w(w_modname)
            mod = self.interpclass_w(w_mod)
            if isinstance(mod, Module):
                self.timer.start("startup " + modname)
                mod.init(self)
                self.timer.stop("startup " + modname)

    def finish(self):
        self.wait_for_thread_shutdown()
        w_exitfunc = self.sys.getdictvalue(self, 'exitfunc')
        if w_exitfunc is not None:
            self.call_function(w_exitfunc)
        from pypy.interpreter.module import Module
        for w_mod in self.builtin_modules.values():
            mod = self.interpclass_w(w_mod)
            if isinstance(mod, Module) and mod.startup_called:
                mod.shutdown(self)
        if self.config.objspace.std.withdictmeasurement:
            from pypy.objspace.std.dictmultiobject import report
            report()
        if self.config.objspace.logbytecodes:
            self.reportbytecodecounts()
        if self.config.objspace.std.logspaceoptypes:
            for s in self.FrameClass._space_op_types:
                print s

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
        except OperationError, e:
            e.write_unraisable(self, "threading._shutdown()")

    def reportbytecodecounts(self):
        os.write(2, "Starting bytecode report.\n")
        fd = os.open('bytecode.txt', os.O_CREAT|os.O_WRONLY|os.O_TRUNC, 0644)
        os.write(fd, "bytecodecounts = {\n")
        for opcode in range(len(self.bytecodecounts)):
            count = self.bytecodecounts[opcode]
            if not count:
                continue
            os.write(fd, "    %s: %s,\n" % (opcode, count))
        os.write(fd, "}\n")
        os.write(fd, "bytecodetransitioncount = {\n")
        for opcode, probs in self.bytecodetransitioncount.iteritems():
            os.write(fd, "    %s: {\n" % (opcode, ))
            for nextcode, count in probs.iteritems():
                os.write(fd, "        %s: %s,\n" % (nextcode, count))
            os.write(fd, "    },\n")
        os.write(fd, "}\n")
        os.close(fd)
        os.write(2, "Reporting done.\n")

    def __repr__(self):
        try:
            return self._this_space_repr_
        except AttributeError:
            return self.__class__.__name__

    def setbuiltinmodule(self, importname):
        """NOT_RPYTHON. load a lazy pypy/module and put it into sys.modules"""
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

        mod = Module(self, self.wrap(name))
        mod.install()

        return name

    def getbuiltinmodule(self, name, force_init=False):
        w_name = self.wrap(name)
        w_modules = self.sys.get('modules')
        try:
            w_mod = self.getitem(w_modules, w_name)
        except OperationError, e:
            if not e.match(self, self.w_KeyError):
                raise
        else:
            if not force_init:
                return w_mod

        # If the module is a builtin but not yet imported,
        # retrieve it and initialize it
        try:
            w_mod = self.builtin_modules[name]
        except KeyError:
            raise operationerrfmt(
                self.w_SystemError,
                "getbuiltinmodule() called "
                "with non-builtin module %s", name)
        else:
            # Add the module to sys.modules
            self.setitem(w_modules, w_name, w_mod)

            # And initialize it
            from pypy.interpreter.module import Module
            mod = self.interpclass_w(w_mod)
            if isinstance(mod, Module):
                self.timer.start("startup " + name)
                mod.init(self)
                self.timer.stop("startup " + name)
            return w_mod

    def get_builtinmodule_to_install(self):
        """NOT_RPYTHON"""
        from pypy.tool.lib_pypy import LIB_PYPY
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

        # a bit of custom logic: time2 or rctime take precedence over time
        # XXX this could probably be done as a "requires" in the config
        if ('time2' in modules or 'rctime' in modules) and 'time' in modules:
            modules.remove('time')

        if not self.config.objspace.nofaking:
            for modname in self.ALL_BUILTIN_MODULES:
                if not LIB_PYPY.join(modname+'.py').check(file=True):
                    modules.append('faked+'+modname)

        self._builtinmodule_list = modules
        return self._builtinmodule_list

    ALL_BUILTIN_MODULES = [
        'posix', 'nt', 'os2', 'mac', 'ce', 'riscos',
        'math', 'array', 'select',
        '_random', '_sre', 'time', '_socket', 'errno',
        'unicodedata',
        'parser', 'fcntl', '_codecs', 'binascii'
    ]

    def make_builtins(self):
        "NOT_RPYTHON: only for initializing the space."

        from pypy.module.exceptions import Module
        w_name = self.wrap('exceptions')
        self.exceptions_module = Module(self, w_name)
        self.exceptions_module.install()

        from pypy.module.sys import Module
        w_name = self.wrap('sys')
        self.sys = Module(self, w_name)
        self.sys.install()

        from pypy.module.imp import Module
        w_name = self.wrap('imp')
        mod = Module(self, w_name)
        mod.install()

        from pypy.module.__builtin__ import Module
        w_name = self.wrap('__builtin__')
        self.builtin = Module(self, w_name)
        w_builtin = self.wrap(self.builtin)
        w_builtin.install()
        self.setitem(self.builtin.w_dict, self.wrap('__builtins__'), w_builtin)

        bootstrap_modules = set(('sys', 'imp', '__builtin__', 'exceptions'))
        installed_builtin_modules = list(bootstrap_modules)

        exception_types_w = self.export_builtin_exceptions()

        # initialize with "bootstrap types" from objspace  (e.g. w_None)
        types_w = itertools.chain(self.get_builtin_types().iteritems(),
                                  exception_types_w.iteritems())
        for name, w_type in types_w:
            self.setitem(self.builtin.w_dict, self.wrap(name), w_type)

        # install mixed and faked modules
        for mixedname in self.get_builtinmodule_to_install():
            if (mixedname not in bootstrap_modules
                and not mixedname.startswith('faked+')):
                self.install_mixedmodule(mixedname, installed_builtin_modules)
        for mixedname in self.get_builtinmodule_to_install():
            if mixedname.startswith('faked+'):
                modname = mixedname[6:]
                self.install_faked_module(modname, installed_builtin_modules)

        installed_builtin_modules.sort()
        w_builtin_module_names = self.newtuple(
            [self.wrap(fn) for fn in installed_builtin_modules])

        # force this value into the dict without unlazyfying everything
        self.setitem(self.sys.w_dict, self.wrap('builtin_module_names'),
                     w_builtin_module_names)

    def get_builtin_types(self):
        """Get a dictionary mapping the names of builtin types to the type
        objects."""
        raise NotImplementedError

    def export_builtin_exceptions(self):
        """NOT_RPYTHON"""
        w_dic = self.exceptions_module.getdict(self)
        w_keys = self.call_method(w_dic, "keys")
        exc_types_w = {}
        for w_name in self.unpackiterable(w_keys):
            name = self.str_w(w_name)
            if not name.startswith('__'):
                excname = name
                w_exc = self.getitem(w_dic, w_name)
                exc_types_w[name] = w_exc
                setattr(self, "w_" + excname, w_exc)
        # Make a prebuilt recursion error
        w_msg = self.wrap("maximum recursion depth exceeded")
        self.prebuilt_recursion_error = OperationError(self.w_RuntimeError,
                                                       w_msg)
        return exc_types_w

    def install_mixedmodule(self, mixedname, installed_builtin_modules):
        """NOT_RPYTHON"""
        modname = self.setbuiltinmodule(mixedname)
        if modname:
            assert modname not in installed_builtin_modules, (
                "duplicate interp-level module enabled for the "
                "app-level module %r" % (modname,))
            installed_builtin_modules.append(modname)

    def load_cpython_module(self, modname):
        "NOT_RPYTHON. Steal a module from CPython."
        cpy_module = __import__(modname, {}, {}, ['*'])
        return cpy_module

    def install_faked_module(self, modname, installed_builtin_modules):
        """NOT_RPYTHON"""
        if modname in installed_builtin_modules:
            return
        try:
            module = self.load_cpython_module(modname)
        except ImportError:
            return
        else:
            w_modules = self.sys.get('modules')
            self.setitem(w_modules, self.wrap(modname), self.wrap(module))
            installed_builtin_modules.append(modname)

    def setup_builtin_modules(self):
        "NOT_RPYTHON: only for initializing the space."
        if self.config.objspace.usemodules.cpyext:
            from pypy.module.cpyext.state import State
            self.fromcache(State).build_api(self)
        self.getbuiltinmodule('sys')
        self.getbuiltinmodule('imp')
        self.getbuiltinmodule('__builtin__')
        for mod in self.builtin_modules.values():
            mod.setup_after_space_initialization()

    def initialize(self):
        """NOT_RPYTHON: Abstract method that should put some minimal
        content into the w_builtins."""

    def enter_cache_building_mode(self):
        "hook for the flow object space"
    def leave_cache_building_mode(self, val):
        "hook for the flow object space"

    @jit.loop_invariant
    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        # Important: the annotator must not see a prebuilt ExecutionContext:
        # you should not see frames while you translate
        # so we make sure that the threadlocals never *have* an
        # ExecutionContext during translation.
        if self.config.translating and not we_are_translated():
            assert self.threadlocals.getvalue() is None, (
                "threadlocals got an ExecutionContext during translation!")
            try:
                return self._ec_during_translation
            except AttributeError:
                ec = self.createexecutioncontext()
                self._ec_during_translation = ec
                return ec
        # normal case follows.  The 'thread' module installs a real
        # thread-local object in self.threadlocals, so this builds
        # and caches a new ec in each thread.
        ec = self.threadlocals.getvalue()
        if ec is None:
            ec = self.createexecutioncontext()
            self.threadlocals.setvalue(ec)
        return ec

    def _freeze_(self):
        return True

    def createexecutioncontext(self):
        "Factory function for execution contexts."
        return ExecutionContext(self)

    def createcompiler(self):
        "Factory function creating a compiler object."
        # XXX simple selection logic for now
        try:
            return self.default_compiler
        except AttributeError:
            from pypy.interpreter.pycompiler import PythonAstCompiler
            compiler = PythonAstCompiler(self)
            self.default_compiler = compiler
            return compiler

    def createframe(self, code, w_globals, closure=None):
        "Create an empty PyFrame suitable for this code object."
        return self.FrameClass(self, code, w_globals, closure)

    def allocate_lock(self):
        """Return an interp-level Lock object if threads are enabled,
        and a dummy object if they are not."""
        if self.config.objspace.usemodules.thread:
            # we use a sub-function to avoid putting the 'import' statement
            # here, where the flow space would see it even if thread=False
            return self.__allocate_lock()
        else:
            return dummy_lock

    def __allocate_lock(self):
        from pypy.module.thread.ll_thread import allocate_lock, error
        try:
            return allocate_lock()
        except error:
            raise OperationError(self.w_RuntimeError,
                                 self.wrap("out of resources"))

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    def not_(self, w_obj):
        return self.wrap(not self.is_true(w_obj))

    def eq_w(self, w_obj1, w_obj2):
        """shortcut for space.is_true(space.eq(w_obj1, w_obj2))"""
        return self.is_w(w_obj1, w_obj2) or self.is_true(self.eq(w_obj1, w_obj2))

    def is_w(self, w_obj1, w_obj2):
        """shortcut for space.is_true(space.is_(w_obj1, w_obj2))"""
        return self.is_true(self.is_(w_obj1, w_obj2))

    def hash_w(self, w_obj):
        """shortcut for space.int_w(space.hash(w_obj))"""
        return self.int_w(self.hash(w_obj))

    def len_w(self, w_obj):
        """shotcut for space.int_w(space.len(w_obj))"""
        return self.int_w(self.len(w_obj))

    def setitem_str(self, w_obj, key, w_value):
        return self.setitem(w_obj, self.wrap(key), w_value)

    def finditem_str(self, w_obj, key):
        return self.finditem(w_obj, self.wrap(key))

    def finditem(self, w_obj, w_key):
        try:
            return self.getitem(w_obj, w_key)
        except OperationError, e:
            if e.match(self, self.w_KeyError):
                return None
            raise

    def findattr(self, w_object, w_name):
        try:
            return self.getattr(w_object, w_name)
        except OperationError, e:
            # a PyPy extension: let SystemExit and KeyboardInterrupt go through
            if e.async(self):
                raise
            return None

    def newbool(self, b):
        if b:
            return self.w_True
        else:
            return self.w_False

    def new_interned_w_str(self, w_s):
        s = self.str_w(w_s)
        try:
            return self.interned_strings[s]
        except KeyError:
            pass
        self.interned_strings[s] = w_s
        return w_s

    def new_interned_str(self, s):
        try:
            return self.interned_strings[s]
        except KeyError:
            pass
        w_s = self.interned_strings[s] = self.wrap(s)
        return w_s

    def interpclass_w(self, w_obj):
        """
         If w_obj is a wrapped internal interpreter class instance unwrap to it,
         otherwise return None.  (Can be overridden in specific spaces; you
     should generally use the helper space.interp_w() instead.)
        """
        if isinstance(w_obj, Wrappable):
            return w_obj
        return None

    def descr_self_interp_w(self, RequiredClass, w_obj):
        obj = self.interpclass_w(w_obj)
        if not isinstance(obj, RequiredClass):
            raise DescrMismatch()
        return obj
    descr_self_interp_w._annspecialcase_ = 'specialize:arg(1)'

    def interp_w(self, RequiredClass, w_obj, can_be_None=False):
        """
        Unwrap w_obj, checking that it is an instance of the required internal
        interpreter class (a subclass of Wrappable).
        """
        assert RequiredClass is not None
        if can_be_None and self.is_w(w_obj, self.w_None):
            return None
        obj = self.interpclass_w(w_obj)
        if not isinstance(obj, RequiredClass):   # or obj is None
            msg = "'%s' object expected, got '%s' instead"
            raise operationerrfmt(self.w_TypeError, msg,
                wrappable_class_name(RequiredClass),
                w_obj.getclass(self).getname(self))
        return obj
    interp_w._annspecialcase_ = 'specialize:arg(1)'

    def unpackiterable(self, w_iterable, expected_length=-1):
        """Unpack an iterable object into a real (interpreter-level) list.
        Raise an OperationError(w_ValueError) if the length is wrong."""
        w_iterator = self.iter(w_iterable)
        # If we know the expected length we can preallocate.
        if expected_length == -1:
            items = []
        else:
            items = [None] * expected_length
        idx = 0
        while True:
            try:
                w_item = self.next(w_iterator)
            except OperationError, e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            if expected_length != -1 and idx == expected_length:
                raise OperationError(self.w_ValueError,
                                     self.wrap("too many values to unpack"))
            if expected_length == -1:
                items.append(w_item)
            else:
                items[idx] = w_item
            idx += 1
        if expected_length != -1 and idx < expected_length:
            if idx == 1:
                plural = ""
            else:
                plural = "s"
            raise OperationError(self.w_ValueError,
                      self.wrap("need more than %d value%s to unpack" %
                                (idx, plural)))
        return items

    unpackiterable_unroll = jit.unroll_safe(func_with_new_name(unpackiterable,
                                            'unpackiterable_unroll'))

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

    @jit.unroll_safe
    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        if self.is_w(w_exc_type, w_check_class):
            return True   # fast path (also here to handle string exceptions)
        try:
            if self.is_true(self.isinstance(w_check_class, self.w_tuple)):
                for w_t in self.fixedview(w_check_class):
                    if self.exception_match(w_exc_type, w_t):
                        return True
                else:
                    return False
            return self.exception_issubclass_w(w_exc_type, w_check_class)
        except OperationError, e:
            if e.match(self, self.w_TypeError):   # string exceptions maybe
                return False
            raise

    def call_obj_args(self, w_callable, w_obj, args):
        if not self.config.objspace.disable_call_speedhacks:
            # XXX start of hack for performance
            from pypy.interpreter.function import Function
            if isinstance(w_callable, Function):
                return w_callable.call_obj_args(w_obj, args)
            # XXX end of hack for performance
        return self.call_args(w_callable, args.prepend(w_obj))

    def call(self, w_callable, w_args, w_kwds=None):
        args = Arguments.frompacked(self, w_args, w_kwds)
        return self.call_args(w_callable, args)

    def call_function(self, w_func, *args_w):
        nargs = len(args_w) # used for pruning funccall versions
        if not self.config.objspace.disable_call_speedhacks and nargs < 5:
            # XXX start of hack for performance
            from pypy.interpreter.function import Function, Method
            if isinstance(w_func, Method):
                w_inst = w_func.w_instance
                if w_inst is not None:
                    if nargs < 4:
                        func = w_func.w_function
                        if isinstance(func, Function):
                            return func.funccall(w_inst, *args_w)
                elif args_w and (
                        self.abstract_isinstance_w(args_w[0], w_func.w_class)):
                    w_func = w_func.w_function

            if isinstance(w_func, Function):
                return w_func.funccall(*args_w)
            # XXX end of hack for performance

        args = Arguments(self, list(args_w))
        return self.call_args(w_func, args)

    def call_valuestack(self, w_func, nargs, frame):
        from pypy.interpreter.function import Function, Method, is_builtin_code
        if frame.is_being_profiled and is_builtin_code(w_func):
            # XXX: this code is copied&pasted :-( from the slow path below
            # call_valuestack().
            args = frame.make_arguments(nargs)
            return self.call_args_and_c_profile(frame, w_func, args)

        if not self.config.objspace.disable_call_speedhacks:
            # XXX start of hack for performance
            if isinstance(w_func, Method):
                w_inst = w_func.w_instance
                if w_inst is not None:
                    w_func = w_func.w_function
                    # reuse callable stack place for w_inst
                    frame.settopvalue(w_inst, nargs)
                    nargs += 1
                elif nargs > 0 and (
                    self.abstract_isinstance_w(frame.peekvalue(nargs-1),   #    :-(
                                               w_func.w_class)):
                    w_func = w_func.w_function

            if isinstance(w_func, Function):
                return w_func.funccall_valuestack(nargs, frame)
            # XXX end of hack for performance

        args = frame.make_arguments(nargs)
        return self.call_args(w_func, args)

    def call_args_and_c_profile(self, frame, w_func, args):
        ec = self.getexecutioncontext()
        ec.c_call_trace(frame, w_func, args)
        try:
            w_res = self.call_args(w_func, args)
        except OperationError, e:
            w_value = e.get_w_value(self)
            ec.c_exception_trace(frame, w_value)
            raise
        ec.c_return_trace(frame, w_func, args)
        return w_res

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.wrap(methname))
        return self.call_function(w_meth, *arg_w)

    def lookup(self, w_obj, name):
        w_type = self.type(w_obj)
        w_mro = self.getattr(w_type, self.wrap("__mro__"))
        for w_supertype in self.fixedview(w_mro):
            w_value = w_supertype.getdictvalue(self, name)
            if w_value is not None:
                return w_value
        return None

    def is_oldstyle_instance(self, w_obj):
        # xxx hack hack hack
        from pypy.module.__builtin__.interp_classobj import W_InstanceObject
        obj = self.interpclass_w(w_obj)
        return obj is not None and isinstance(obj, W_InstanceObject)

    def callable(self, w_obj):
        if self.lookup(w_obj, "__call__") is not None:
            if self.is_oldstyle_instance(w_obj):
                # ugly old style class special treatment, but well ...
                try:
                    self.getattr(w_obj, self.wrap("__call__"))
                    return self.w_True
                except OperationError, e:
                    if not e.match(self, self.w_AttributeError):
                        raise
                    return self.w_False
            else:
                return self.w_True
        return self.w_False

    def isinstance_w(self, w_obj, w_type):
        return self.is_true(self.isinstance(w_obj, w_type))

    # The code below only works
    # for the simple case (new-style instance).
    # These methods are patched with the full logic by the __builtin__
    # module when it is loaded

    def abstract_issubclass_w(self, w_cls1, w_cls2):
        # Equivalent to 'issubclass(cls1, cls2)'.
        return self.is_true(self.issubtype(w_cls1, w_cls2))

    def abstract_isinstance_w(self, w_obj, w_cls):
        # Equivalent to 'isinstance(obj, cls)'.
        return self.is_true(self.isinstance(w_obj, w_cls))

    def abstract_isclass_w(self, w_obj):
        # Equivalent to 'isinstance(obj, type)'.
        return self.is_true(self.isinstance(w_obj, self.w_type))

    def abstract_getclass(self, w_obj):
        # Equivalent to 'obj.__class__'.
        return self.type(w_obj)

    # CPython rules allows old style classes or subclasses
    # of BaseExceptions to be exceptions.
    # This is slightly less general than the case above, so we prefix
    # it with exception_

    def exception_is_valid_obj_as_class_w(self, w_obj):
        if not self.isinstance_w(w_obj, self.w_type):
            return False
        if not self.full_exceptions:
            return True
        return self.is_true(self.issubtype(w_obj, self.w_BaseException))

    def exception_is_valid_class_w(self, w_cls):
        if not self.full_exceptions:
            return True
        return self.is_true(self.issubtype(w_cls, self.w_BaseException))

    def exception_getclass(self, w_obj):
        return self.type(w_obj)

    def exception_issubclass_w(self, w_cls1, w_cls2):
        return self.is_true(self.issubtype(w_cls1, w_cls2))

    def new_exception_class(self, *args, **kwargs):
        "NOT_RPYTHON; convenience method to create excceptions in modules"
        return new_exception_class(self, *args, **kwargs)

    # end of special support code

    def eval(self, expression, w_globals, w_locals, hidden_applevel=False):
        "NOT_RPYTHON: For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(expression, str):
            compiler = self.createcompiler()
            expression = compiler.compile(expression, '?', 'eval', 0,
                                         hidden_applevel=hidden_applevel)
        if isinstance(expression, types.CodeType):
            # XXX only used by appsupport
            expression = PyCode._from_code(self, expression)
        if not isinstance(expression, PyCode):
            raise TypeError, 'space.eval(): expected a string, code or PyCode object'
        return expression.exec_code(self, w_globals, w_locals)

    def exec_(self, statement, w_globals, w_locals, hidden_applevel=False,
              filename=None):
        "NOT_RPYTHON: For internal debugging."
        import types
        if filename is None:
            filename = '?'
        from pypy.interpreter.pycode import PyCode
        if isinstance(statement, str):
            compiler = self.createcompiler()
            statement = compiler.compile(statement, filename, 'exec', 0,
                                         hidden_applevel=hidden_applevel)
        if isinstance(statement, types.CodeType):
            # XXX only used by appsupport
            statement = PyCode._from_code(self, statement)
        if not isinstance(statement, PyCode):
            raise TypeError, 'space.exec_(): expected a string, code or PyCode object'
        w_key = self.wrap('__builtins__')
        if not self.is_true(self.contains(w_globals, w_key)):
            self.setitem(w_globals, w_key, self.wrap(self.builtin))
        return statement.exec_code(self, w_globals, w_locals)

    def appexec(self, posargs_w, source):
        """ return value from executing given source at applevel.
            EXPERIMENTAL. The source must look like
               '''(x, y):
                       do_stuff...
                       return result
               '''
        """
        w_func = self.fromcache(AppExecCache).getorbuild(source)
        args = Arguments(self, list(posargs_w))
        return self.call_args(w_func, args)
    appexec._annspecialcase_ = 'specialize:arg(2)'

    def _next_or_none(self, w_it):
        try:
            return self.next(w_it)
        except OperationError, e:
            if not e.match(self, self.w_StopIteration):
                raise
            return None

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
    compare_by_iteration._annspecialcase_ = 'specialize:arg(3)'

    def decode_index(self, w_index_or_slice, seqlength):
        """Helper for custom sequence implementations
             -> (index, 0, 0) or
                (start, stop, step)
        """
        if self.is_true(self.isinstance(w_index_or_slice, self.w_slice)):
            from pypy.objspace.std.sliceobject import W_SliceObject
            assert isinstance(w_index_or_slice, W_SliceObject)
            start, stop, step = w_index_or_slice.indices3(self, seqlength)
        else:
            start = self.int_w(w_index_or_slice)
            if start < 0:
                start += seqlength
            if not (0 <= start < seqlength):
                raise OperationError(self.w_IndexError,
                                     self.wrap("index out of range"))
            stop = 0
            step = 0
        return start, stop, step

    def decode_index4(self, w_index_or_slice, seqlength):
        """Helper for custom sequence implementations
             -> (index, 0, 0, 1) or
                (start, stop, step, slice_length)
        """
        if self.is_true(self.isinstance(w_index_or_slice, self.w_slice)):
            from pypy.objspace.std.sliceobject import W_SliceObject
            assert isinstance(w_index_or_slice, W_SliceObject)
            start, stop, step, length = w_index_or_slice.indices4(self,
                                                                  seqlength)
        else:
            start = self.int_w(w_index_or_slice)
            if start < 0:
                start += seqlength
            if not (0 <= start < seqlength):
                raise OperationError(self.w_IndexError,
                                     self.wrap("index out of range"))
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
        except OperationError, err:
            if objdescr is None or not err.match(self, self.w_TypeError):
                raise
            msg = "%s must be an integer, not %s"
            raise operationerrfmt(self.w_TypeError, msg,
                objdescr, self.type(w_obj).getname(self))
        try:
            index = self.int_w(w_index)
        except OperationError, err:
            if not err.match(self, self.w_OverflowError):
                raise
            if not w_exception:
                # w_index should be a long object, but can't be sure of that
                if self.is_true(self.lt(w_index, self.wrap(0))):
                    return -sys.maxint-1
                else:
                    return sys.maxint
            else:
                raise operationerrfmt(
                    w_exception,
                    "cannot fit '%s' into an index-sized "
                    "integer", self.type(w_obj).getname(self))
        else:
            return index

    def r_longlong_w(self, w_obj):
        bigint = self.bigint_w(w_obj)
        try:
            return bigint.tolonglong()
        except OverflowError:
            raise OperationError(self.w_OverflowError,
                                 self.wrap('integer too large'))

    def r_ulonglong_w(self, w_obj):
        bigint = self.bigint_w(w_obj)
        try:
            return bigint.toulonglong()
        except OverflowError:
            raise OperationError(self.w_OverflowError,
                                 self.wrap('integer too large'))
        except ValueError:
            raise OperationError(self.w_ValueError,
                                 self.wrap('cannot convert negative integer '
                                           'to unsigned int'))

    def buffer_w(self, w_obj):
        # returns a Buffer instance
        from pypy.interpreter.buffer import Buffer
        w_buffer = self.buffer(w_obj)
        return self.interp_w(Buffer, w_buffer)

    def rwbuffer_w(self, w_obj):
        # returns a RWBuffer instance
        from pypy.interpreter.buffer import RWBuffer
        buffer = self.buffer_w(w_obj)
        if not isinstance(buffer, RWBuffer):
            raise OperationError(self.w_TypeError,
                                 self.wrap('read-write buffer expected'))
        return buffer

    def bufferstr_new_w(self, w_obj):
        # Implement the "new buffer interface" (new in Python 2.7)
        # returning an unwrapped string. It doesn't accept unicode
        # strings
        buffer = self.buffer_w(w_obj)
        return buffer.as_str()

    def bufferstr_w(self, w_obj):
        # Directly returns an interp-level str.  Note that if w_obj is a
        # unicode string, this is different from str_w(buffer(w_obj)):
        # indeed, the latter returns a string with the raw bytes from
        # the underlying unicode buffer, but bufferstr_w() just converts
        # the unicode to an ascii string.  This inconsistency is kind of
        # needed because CPython has the same issue.  (Well, it's
        # unclear if there is any use at all for getting the bytes in
        # the unicode buffer.)
        try:
            return self.str_w(w_obj)
        except OperationError, e:
            if not e.match(self, self.w_TypeError):
                raise
            buffer = self.buffer_w(w_obj)
            return buffer.as_str()

    def str_or_None_w(self, w_obj):
        if self.is_w(w_obj, self.w_None):
            return None
        return self.str_w(w_obj)

    def realstr_w(self, w_obj):
        # Like str_w, but only works if w_obj is really of type 'str'.
        if not self.is_true(self.isinstance(w_obj, self.w_str)):
            raise OperationError(self.w_TypeError,
                                 self.wrap('argument must be a string'))
        return self.str_w(w_obj)

    def realunicode_w(self, w_obj):
        # Like unicode_w, but only works if w_obj is really of type
        # 'unicode'.
        if not self.is_true(self.isinstance(w_obj, self.w_unicode)):
            raise OperationError(self.w_TypeError,
                                 self.wrap('argument must be a unicode'))
        return self.unicode_w(w_obj)

    def bool_w(self, w_obj):
        # Unwraps a bool, also accepting an int for compatibility.
        # This is here mostly just for gateway.int_unwrapping_space_method().
        return bool(self.int_w(w_obj))

    # This is all interface for gateway.py.
    def gateway_int_w(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_float)):
            raise OperationError(self.w_TypeError,
                            self.wrap("integer argument expected, got float"))
        return self.int_w(self.int(w_obj))

    def gateway_float_w(self, w_obj):
        return self.float_w(self.float(w_obj))

    def gateway_r_longlong_w(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_float)):
            raise OperationError(self.w_TypeError,
                            self.wrap("integer argument expected, got float"))
        return self.r_longlong_w(self.int(w_obj))

    def gateway_r_uint_w(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_float)):
            raise OperationError(self.w_TypeError,
                            self.wrap("integer argument expected, got float"))
        return self.uint_w(self.int(w_obj))

    def gateway_r_ulonglong_w(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_float)):
            raise OperationError(self.w_TypeError,
                            self.wrap("integer argument expected, got float"))
        return self.r_ulonglong_w(self.int(w_obj))

    def gateway_nonnegint_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level ValueError if
        # the integer is negative.  Here for gateway.py.
        value = self.gateway_int_w(w_obj)
        if value < 0:
            raise OperationError(self.w_ValueError,
                                 self.wrap("expected a non-negative integer"))
        return value

    def c_int_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level OverflowError if
        # the integer does not fit in 32 bits.  Here for gateway.py.
        value = self.gateway_int_w(w_obj)
        if value < -2147483647-1 or value > 2147483647:
            raise OperationError(self.w_OverflowError,
                                 self.wrap("expected a 32-bit integer"))
        return value

    def c_uint_w(self, w_obj):
        # Like space.gateway_uint_w(), but raises an app-level OverflowError if
        # the integer does not fit in 32 bits.  Here for gateway.py.
        value = self.gateway_r_uint_w(w_obj)
        if value > UINT_MAX_32_BITS:
            raise OperationError(self.w_OverflowError,
                              self.wrap("expected an unsigned 32-bit integer"))
        return value

    def c_nonnegint_w(self, w_obj):
        # Like space.gateway_int_w(), but raises an app-level ValueError if
        # the integer is negative or does not fit in 32 bits.  Here
        # for gateway.py.
        value = self.gateway_int_w(w_obj)
        if value < 0:
            raise OperationError(self.w_ValueError,
                                 self.wrap("expected a non-negative integer"))
        if value > 2147483647:
            raise OperationError(self.w_OverflowError,
                                 self.wrap("expected a 32-bit integer"))
        return value

    def c_filedescriptor_w(self, w_fd):
        # This is only used sometimes in CPython, e.g. for os.fsync() but
        # not os.close().  It's likely designed for 'select'.  It's irregular
        # in the sense that it expects either a real int/long or an object
        # with a fileno(), but not an object with an __int__().
        if (not self.isinstance_w(w_fd, self.w_int) and
            not self.isinstance_w(w_fd, self.w_long)):
            try:
                w_fileno = self.getattr(w_fd, self.wrap("fileno"))
            except OperationError, e:
                if e.match(self, self.w_AttributeError):
                    raise OperationError(self.w_TypeError,
                        self.wrap("argument must be an int, or have a fileno() "
                            "method.")
                    )
                raise
            w_fd = self.call_function(w_fileno)
            if not self.isinstance_w(w_fd, self.w_int):
                raise OperationError(self.w_TypeError,
                    self.wrap("fileno() must return an integer")
                )
        fd = self.int_w(w_fd)
        if fd < 0:
            raise operationerrfmt(self.w_ValueError,
                "file descriptor cannot be a negative integer (%d)", fd
            )
        return fd

    def warn(self, msg, w_warningcls):
        self.appexec([self.wrap(msg), w_warningcls], """(msg, warningcls):
            import warnings
            warnings.warn(msg, warningcls, stacklevel=2)
        """)

    def resolve_target(self, w_obj):
        """ A space method that can be used by special object spaces (like
        thunk) to replace an object by another. """
        return w_obj


class AppExecCache(SpaceCache):
    def build(cache, source):
        """ NOT_RPYTHON """
        space = cache.space
        # XXX will change once we have our own compiler
        import py
        source = source.lstrip()
        assert source.startswith('('), "incorrect header in:\n%s" % (source,)
        source = py.code.Source("def anonymous%s\n" % source)
        w_glob = space.newdict()
        space.exec_(str(source), w_glob, w_glob)
        return space.getitem(w_glob, space.wrap('anonymous'))

class DummyLock(object):
    def acquire(self, flag):
        return True
    def release(self):
        pass
    def _freeze_(self):
        return True
dummy_lock = DummyLock()

## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result
## (if any).  Note: keep in sync with pypy.objspace.flow.operation.Table.

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
    ('getslice',        'getslice',  3, ['__getslice__']),
    ('setslice',        'setslice',  4, ['__setslice__']),
    ('delslice',        'delslice',  3, ['__delslice__']),
    ('trunc',           'trunc',     1, ['__trunc__']),
    ('pos',             'pos',       1, ['__pos__']),
    ('neg',             'neg',       1, ['__neg__']),
    ('nonzero',         'truth',     1, ['__nonzero__']),
    ('abs' ,            'abs',       1, ['__abs__']),
    ('hex',             'hex',       1, ['__hex__']),
    ('oct',             'oct',       1, ['__oct__']),
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
    ('int',             'int',       1, ['__int__']),
    ('index',           'index',     1, ['__index__']),
    ('float',           'float',     1, ['__float__']),
    ('long',            'long',      1, ['__long__']),
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
    ('lt',              '<',         2, ['__lt__', '__gt__']),
    ('le',              '<=',        2, ['__le__', '__ge__']),
    ('eq',              '==',        2, ['__eq__', '__eq__']),
    ('ne',              '!=',        2, ['__ne__', '__ne__']),
    ('gt',              '>',         2, ['__gt__', '__lt__']),
    ('ge',              '>=',        2, ['__ge__', '__le__']),
    ('cmp',             'cmp',       2, ['__cmp__']),   # rich cmps preferred
    ('coerce',          'coerce',    2, ['__coerce__', '__coerce__']),
    ('contains',        'contains',  2, ['__contains__']),
    ('iter',            'iter',      1, ['__iter__']),
    ('next',            'next',      1, ['next']),
#    ('call',            'call',      3, ['__call__']),
    ('get',             'get',       3, ['__get__']),
    ('set',             'set',       3, ['__set__']),
    ('delete',          'delete',    2, ['__delete__']),
    ('userdel',         'del',       1, ['__del__']),
    ('buffer',          'buffer',    1, ['__buffer__']),   # see buffer.py
    ]

ObjSpace.BuiltinModuleTable = [
    '__builtin__',
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
    'EOFError',
    'EnvironmentError',
    'Exception',
    'FloatingPointError',
    'IOError',
    'ImportError',
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
    'RuntimeError',
    'StandardError',
    'StopIteration',
    'SyntaxError',
    'SystemError',
    'SystemExit',
    'TabError',
    'TypeError',
    'UnboundLocalError',
    'UnicodeError',
    'ValueError',
    'ZeroDivisionError',
    ]

## Irregular part of the interface:
#
#                                   wrap(x) -> w_x
#                              str_w(w_str) -> str
#              int_w(w_ival or w_long_ival) -> ival
#                       float_w(w_floatval) -> floatval
#             uint_w(w_ival or w_long_ival) -> r_uint_val (unsigned int value)
#             bigint_w(w_ival or w_long_ival) -> rbigint
#interpclass_w(w_interpclass_inst or w_obj) -> interpclass_inst|w_obj
#                               unwrap(w_x) -> x
#                              is_true(w_x) -> True or False
#                  newtuple([w_1, w_2,...]) -> w_tuple
#                   newlist([w_1, w_2,...]) -> w_list
#                                 newdict() -> empty w_dict
#           newslice(w_start,w_stop,w_step) -> w_slice
#              call_args(w_obj,Arguments()) -> w_result

ObjSpace.IrregularOpTable = [
    'wrap',
    'str_w',
    'int_w',
    'float_w',
    'uint_w',
    'bigint_w',
    'unicode_w',
    'interpclass_w',
    'unwrap',
    'is_true',
    'is_w',
    'newtuple',
    'newlist',
    'newdict',
    'newslice',
    'call_args',
    'marshal_w',
    ]
