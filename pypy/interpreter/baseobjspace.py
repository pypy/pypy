from pypy.interpreter.executioncontext import ExecutionContext
from pypy.interpreter.error import OperationError
from pypy.interpreter.argument import Arguments, ArgumentsFromValuestack
from pypy.interpreter.pycompiler import CPythonCompiler, PythonAstCompiler
from pypy.interpreter.miscutils import ThreadLocals
from pypy.tool.cache import Cache
from pypy.tool.uid import HUGEVAL_BYTES
import os

__all__ = ['ObjSpace', 'OperationError', 'Wrappable', 'W_Root']


class W_Root(object):
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    __slots__ = ()

    def getdict(self):
        return None

    def getdictvalue_w(self, space, attr):
        return self.getdictvalue(space, space.wrap(attr))

    def getdictvalue(self, space, w_attr):
        w_dict = self.getdict()
        if w_dict is not None:
            return space.finditem(w_dict, w_attr)
        return None

    def getdictvalue_attr_is_in_class(self, space, w_attr):
        return self.getdictvalue(space, w_attr)

    def setdictvalue(self, space, w_attr, w_value, shadows_type=True):
        w_dict = self.getdict()
        if w_dict is not None:
            space.set_str_keyed_item(w_dict, w_attr, w_value, shadows_type)
            return True
        return False
    
    def deldictvalue(self, space, w_name):
        w_dict = self.getdict()
        if w_dict is not None:
            try:
                space.delitem(w_dict, w_name)
                return True
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
        return False

    def setdict(self, space, w_dict):
        typename = space.type(self).getname(space, '?')
        raise OperationError(space.w_TypeError,
                             space.wrap("attribute '__dict__' of %s objects "
                                        "is not writable" % typename))

    # to be used directly only by space.type implementations
    def getclass(self, space):
        return space.gettypeobject(self.typedef)

    def setclass(self, space, w_subtype):
        raise OperationError(space.w_TypeError,
                             space.wrap("__class__ assignment: only for heap types"))

    def getname(self, space, default):
        try:
            return space.str_w(space.getattr(self, space.wrap('__name__')))
        except OperationError, e:
            if e.match(space, space.w_TypeError) or e.match(space, space.w_AttributeError):
                return default
            raise

    def getrepr(self, space, info):
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
        return space.wrap("<%s at 0x%s>" % (info, ''.join(addrstring)))

    def getslotvalue(self, index):
        raise NotImplementedError

    def setslotvalue(self, index, w_val):
        raise NotImplementedError

    def descr_call_mismatch(self, space, opname, RequiredClass, args):
        msg = "'%s' object expected, got '%s' instead" % (
            RequiredClass.typedef.name,
            self.getclass(space).getname(space, '?'))
        raise OperationError(space.w_TypeError, space.wrap(msg))

    # used by _weakref implemenation

    def getweakref(self):
        return None

    def setweakref(self, space, weakreflifeline):
        typename = space.type(self).getname(space, '?')
        raise OperationError(space.w_TypeError, space.wrap(
            "cannot create weak reference to '%s' object" % typename))

class Wrappable(W_Root):
    """A subclass of Wrappable is an internal, interpreter-level class
    that can nevertheless be exposed at application-level by space.wrap()."""
    __slots__ = ()

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
        
class UnpackValueError(ValueError):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class DescrMismatch(Exception):
    pass

class ObjSpace(object):
    """Base class for the interpreter-level implementations of object spaces.
    http://codespeak.net/pypy/dist/pypy/doc/objspace.html"""
    
    full_exceptions = True  # full support for exceptions (normalization & more)

    def __init__(self, config=None, **kw): 
        "NOT_RPYTHON: Basic initialization of objects."
        self.fromcache = InternalSpaceCache(self).getorbuild
        self.threadlocals = ThreadLocals()
        # set recursion limit
        # sets all the internal descriptors
        if config is None:
            from pypy.config.pypyoption import get_pypy_config
            config = get_pypy_config(translating=False)
        self.config = config

        # import extra modules for side-effects, possibly based on config
        import pypy.interpreter.nestedscope     # register *_DEREF bytecodes
        if self.config.objspace.opcodes.CALL_METHOD:
            import pypy.interpreter.callmethod  # register *_METHOD bytecodes

        self.interned_strings = {}
        self.pending_actions = []
        self.setoptions(**kw)

#        if self.config.objspace.logbytecodes:            
#            self.bytecodecounts = {}

        self.initialize()

    def setoptions(self):
        # override this in subclasses for extra-options
        pass

    def startup(self):
        # To be called before using the space
        pass

    def finish(self):
        w_exitfunc = self.sys.getdictvalue_w(self, 'exitfunc')
        if w_exitfunc is not None:
            self.call_function(w_exitfunc)
        w_exithandlers = self.sys.getdictvalue_w(self, 'pypy__exithandlers__')
        if w_exithandlers is not None:
            while self.is_true(w_exithandlers):
                w_key_value = self.call_method(w_exithandlers, 'popitem')
                w_key, w_value = self.unpacktuple(w_key_value, 2)
                self.call_function(w_value)
        if self.config.objspace.std.withdictmeasurement:
            from pypy.objspace.std.dictmultiobject import report
            report()
        if self.config.objspace.logbytecodes:
            self.reportbytecodecounts()
    
    def reportbytecodecounts(self):
        os.write(2, "Starting bytecode report.\n")
        fd = os.open('bytecode.txt', os.O_CREAT|os.O_WRONLY|os.O_TRUNC, 0644)
        for opcode, count in self.bytecodecounts.items():
            os.write(fd, str(opcode) + ", " + str(count) + "\n")
        os.close(fd)
        os.write(2, "Reporting done.\n")        

    def __repr__(self):
        try:
            return self._this_space_repr_
        except AttributeError:
            return self.__class__.__name__

    def setbuiltinmodule(self, importname):
        """NOT_RPYTHON. load a lazy pypy/module and put it into sys.modules"""
        import sys

        fullname = "pypy.module.%s" % importname 

        Module = __import__(fullname, 
                            None, None, ["Module"]).Module
        if Module.applevel_name is not None:
            name = Module.applevel_name
        else:
            name = importname

        w_name = self.wrap(name) 
        w_mod = self.wrap(Module(self, w_name)) 
        w_modules = self.sys.get('modules')
        self.setitem(w_modules, w_name, w_mod) 
        return name

    def getbuiltinmodule(self, name):
        w_name = self.wrap(name)
        w_modules = self.sys.get('modules')
        return self.getitem(w_modules, w_name)

    def get_builtinmodule_to_install(self):
        """NOT_RPYTHON"""
        try:
            return self._builtinmodule_list
        except AttributeError:
            pass

        modules = []

        # You can enable more modules by specifying --usemodules=xxx,yyy
        for name, value in self.config.objspace.usemodules:
            if value and name not in modules:
                modules.append(name)

        # a bit of custom logic: time2 or rctime take precedence over time
        # XXX this could probably be done as a "requires" in the config
        if ('time2' in modules or 'rctime' in modules) and 'time' in modules:
            modules.remove('time')

        import pypy
        if not self.config.objspace.nofaking:
            for modname in self.ALL_BUILTIN_MODULES:
                if not (os.path.exists(
                        os.path.join(os.path.dirname(pypy.__file__),
                                     'lib', modname+'.py'))):            
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

        from pypy.module.sys import Module 
        w_name = self.wrap('sys')
        self.sys = Module(self, w_name) 
        w_modules = self.sys.get('modules')
        self.setitem(w_modules, w_name, self.wrap(self.sys))

        from pypy.module.__builtin__ import Module 
        w_name = self.wrap('__builtin__')
        self.builtin = Module(self, w_name) 
        w_builtin = self.wrap(self.builtin)
        self.setitem(w_modules, w_name, w_builtin) 
        self.setitem(self.builtin.w_dict, self.wrap('__builtins__'), w_builtin) 

        bootstrap_modules = ['sys', '__builtin__', 'exceptions']
        installed_builtin_modules = bootstrap_modules[:]

        # initialize with "bootstrap types" from objspace  (e.g. w_None)
        for name, value in self.__dict__.items():
            if name.startswith('w_') and not name.endswith('Type'): 
                name = name[2:]
                #print "setitem: space instance %-20s into builtins" % name
                self.setitem(self.builtin.w_dict, self.wrap(name), value)

        # install mixed and faked modules and set builtin_module_names on sys
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
        from pypy.interpreter.module import Module
        for w_modname in self.unpackiterable(self.sys.get('builtin_module_names')):
            modname = self.unwrap(w_modname)
            mod = self.getbuiltinmodule(modname)
            if isinstance(mod, Module):
                mod.setup_after_space_initialization()

    def initialize(self):
        """NOT_RPYTHON: Abstract method that should put some minimal
        content into the w_builtins."""

    def enter_cache_building_mode(self):
        "hook for the flow object space"
    def leave_cache_building_mode(self, val):
        "hook for the flow object space"

    def getexecutioncontext(self):
        "Return what we consider to be the active execution context."
        ec = self.threadlocals.getvalue()
        if ec is None:
            ec = self.createexecutioncontext()
            self.threadlocals.setvalue(ec)
        return ec

    def _freeze_(self):
        # Important: the annotator must not see a prebuilt ExecutionContext
        # for reasons related to the specialization of the framestack attribute
        # so we make sure there is no executioncontext at freeze-time
        self.threadlocals.setvalue(None)
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
            if self.config.objspace.compiler == 'cpython':
                compiler = CPythonCompiler(self)
            elif self.config.objspace.compiler == 'ast':
                compiler = PythonAstCompiler(self)
            else:
                raise ValueError('unknown --compiler option value: %r' % (
                    self.config.objspace.compiler,))
            self.default_compiler = compiler
            return compiler

    def createframe(self, code, w_globals, closure=None):
        "Create an empty PyFrame suitable for this code object."
        from pypy.interpreter import pyframe
        return pyframe.PyFrame(self, code, w_globals, closure)

    # Following is a friendly interface to common object space operations
    # that can be defined in term of more primitive ones.  Subclasses
    # may also override specific functions for performance.

    #def is_(self, w_x, w_y):   -- not really useful.  Must be subclassed
    #    "'x is y'."
    #    w_id_x = self.id(w_x)
    #    w_id_y = self.id(w_y)
    #    return self.eq(w_id_x, w_id_y)

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

    def set_str_keyed_item(self, w_obj, w_key, w_value, shadows_type=True):
        return self.setitem(w_obj, w_key, w_value)
    
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

    # support for the deprecated __getslice__, __setslice__, __delslice__
    def getslice(self, w_obj, w_start, w_stop):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        return self.getitem(w_obj, w_slice)
    def setslice(self, w_obj, w_start, w_stop, w_sequence):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        self.setitem(w_obj, w_slice, w_sequence)
    def delslice(self, w_obj, w_start, w_stop):
        w_slice = self.newslice(w_start, w_stop, self.w_None)
        self.delitem(w_obj, w_slice)

    def interpclass_w(space, w_obj):
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
        if can_be_None and self.is_w(w_obj, self.w_None):
            return None
        obj = self.interpclass_w(w_obj)
        if not isinstance(obj, RequiredClass):   # or obj is None
            msg = "'%s' object expected, got '%s' instead" % (
                RequiredClass.typedef.name,
            w_obj.getclass(self).getname(self, '?'))
            raise OperationError(self.w_TypeError, self.wrap(msg))
        return obj
    interp_w._annspecialcase_ = 'specialize:arg(1)'

    def unpackiterable(self, w_iterable, expected_length=-1):
        """Unpack an iterable object into a real (interpreter-level) list.
        Raise a real (subclass of) ValueError if the length is wrong."""
        w_iterator = self.iter(w_iterable)
        items = []
        while True:
            try:
                w_item = self.next(w_iterator)
            except OperationError, e:
                if not e.match(self, self.w_StopIteration):
                    raise
                break  # done
            if expected_length != -1 and len(items) == expected_length:
                raise UnpackValueError("too many values to unpack")
            items.append(w_item)
        if expected_length != -1 and len(items) < expected_length:
            i = len(items)
            if i == 1:
                plural = ""
            else:
                plural = "s"
            raise UnpackValueError("need more than %d value%s to unpack" %
                                   (i, plural))
        return items

    def unpacktuple(self, w_tuple, expected_length=-1):
        """Same as unpackiterable(), but only for tuples.
        Only use for bootstrapping or performance reasons."""
        tuple_length = self.int_w(self.len(w_tuple))
        if expected_length != -1 and tuple_length != expected_length:
            raise UnpackValueError("got a tuple of length %d instead of %d" % (
                tuple_length, expected_length))
        items = [
            self.getitem(w_tuple, self.wrap(i)) for i in range(tuple_length)]
        return items

    def exception_match(self, w_exc_type, w_check_class):
        """Checks if the given exception type matches 'w_check_class'."""
        if self.is_w(w_exc_type, w_check_class):
            return True
        if self.is_true(self.abstract_issubclass(w_exc_type, w_check_class)):
            return True

        if self.is_true(self.isinstance(w_check_class, self.w_tuple)):
            exclst_w = self.unpacktuple(w_check_class)
            for w_e in exclst_w:
                if self.exception_match(w_exc_type, w_e):
                    return True
        return False

    def call(self, w_callable, w_args, w_kwds=None):
        args = Arguments.frompacked(self, w_args, w_kwds)
        return self.call_args(w_callable, args)

    def call_function(self, w_func, *args_w):
        # XXX start of hack for performance
        from pypy.interpreter.function import Function, Method
        if isinstance(w_func, Method):
            w_inst = w_func.w_instance
            if w_inst is not None:
                func = w_func.w_function
                if isinstance(func, Function):
                    return func.funccall(w_inst, *args_w)
            elif args_w and self.is_true(
                    self.abstract_isinstance(args_w[0], w_func.w_class)):
                w_func = w_func.w_function

        if isinstance(w_func, Function):
            return w_func.funccall(*args_w)
        # XXX end of hack for performance

        args = Arguments(self, list(args_w))
        return self.call_args(w_func, args)

    def call_valuestack(self, w_func, nargs, frame):
        # XXX start of hack for performance
        from pypy.interpreter.function import Function, Method
        if isinstance(w_func, Method):
            w_inst = w_func.w_instance
            if w_inst is not None:
                func = w_func.w_function
                if isinstance(func, Function):
                    return func.funccall_obj_valuestack(w_inst, nargs, frame)
            elif nargs > 0 and self.is_true(
                self.abstract_isinstance(frame.peekvalue(nargs-1),   #    :-(
                                         w_func.w_class)):
                w_func = w_func.w_function

        if isinstance(w_func, Function):
            return w_func.funccall_valuestack(nargs, frame)
        # XXX end of hack for performance

        args = ArgumentsFromValuestack(self, frame, nargs)
        try:
            return self.call_args(w_func, args)
        finally:
            args.frame = None

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = self.getattr(w_obj, self.wrap(methname))
        return self.call_function(w_meth, *arg_w)

    def lookup(self, w_obj, name):
        w_type = self.type(w_obj)
        w_mro = self.getattr(w_type, self.wrap("__mro__"))
        for w_supertype in self.unpackiterable(w_mro):
            w_value = w_supertype.getdictvalue_w(self, name)
            if w_value is not None:
                return w_value
        return None

    def callable(self, w_obj):
        if self.lookup(w_obj, "__call__") is not None:
            w_is_oldstyle = self.isinstance(w_obj, self.w_instance)
            if self.is_true(w_is_oldstyle):
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

    def isinstance(self, w_obj, w_type):
        w_objtype = self.type(w_obj)
        return self.issubtype(w_objtype, w_type)

    def abstract_issubclass(self, w_obj, w_cls, failhard=False):
        try:
            return self.issubtype(w_obj, w_cls)
        except OperationError, e:
            if not e.match(self, self.w_TypeError):
                raise
            try:
                self.getattr(w_cls, self.wrap('__bases__')) # type sanity check
                return self.recursive_issubclass(w_obj, w_cls)
            except OperationError, e:
                if failhard or not (e.match(self, self.w_TypeError) or
                                    e.match(self, self.w_AttributeError)):
                    raise
                else:
                    return self.w_False

    def recursive_issubclass(self, w_obj, w_cls):
        if self.is_w(w_obj, w_cls):
            return self.w_True
        for w_base in self.unpackiterable(self.getattr(w_obj, 
                                                       self.wrap('__bases__'))):
            if self.is_true(self.recursive_issubclass(w_base, w_cls)):
                return self.w_True
        return self.w_False

    def abstract_isinstance(self, w_obj, w_cls):
        try:
            return self.isinstance(w_obj, w_cls)
        except OperationError, e:
            if not e.match(self, self.w_TypeError):
                raise
            try:
                w_objcls = self.getattr(w_obj, self.wrap('__class__'))
                return self.abstract_issubclass(w_objcls, w_cls)
            except OperationError, e:
                if not (e.match(self, self.w_TypeError) or
                        e.match(self, self.w_AttributeError)):
                    raise
                return self.w_False

    def abstract_isclass(self, w_obj):
        if self.is_true(self.isinstance(w_obj, self.w_type)):
            return self.w_True
        if self.findattr(w_obj, self.wrap('__bases__')) is not None:
            return self.w_True
        else:
            return self.w_False

    def abstract_getclass(self, w_obj):
        try:
            return self.getattr(w_obj, self.wrap('__class__'))
        except OperationError, e:
            if e.match(self, self.w_TypeError) or e.match(self, self.w_AttributeError):
                return self.type(w_obj)
            raise

    def eval(self, expression, w_globals, w_locals):
        "NOT_RPYTHON: For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(expression, str):
            expression = compile(expression, '?', 'eval')
        if isinstance(expression, types.CodeType):
            expression = PyCode._from_code(self, expression)
        if not isinstance(expression, PyCode):
            raise TypeError, 'space.eval(): expected a string, code or PyCode object'
        return expression.exec_code(self, w_globals, w_locals)

    def exec_(self, statement, w_globals, w_locals, hidden_applevel=False):
        "NOT_RPYTHON: For internal debugging."
        import types
        from pypy.interpreter.pycode import PyCode
        if isinstance(statement, str):
            statement = compile(statement, '?', 'exec')
        if isinstance(statement, types.CodeType):
            statement = PyCode._from_code(self, statement,
                                          hidden_applevel=hidden_applevel)
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

    def decode_index(self, w_index_or_slice, seqlength):
        """Helper for custom sequence implementations
             -> (index, 0, 0) or
                (start, stop, step)
        """
        if self.is_true(self.isinstance(w_index_or_slice, self.w_slice)):
            w_indices = self.call_method(w_index_or_slice, "indices",
                                         self.wrap(seqlength))
            w_start, w_stop, w_step = self.unpackiterable(w_indices, 3)
            start = self.int_w(w_start)
            stop  = self.int_w(w_stop)
            step  = self.int_w(w_step)
            if step == 0:
                raise OperationError(self.w_ValueError,
                                     self.wrap("slice step cannot be zero"))
        else:
            start = self.int_w(w_index_or_slice)
            if start < 0:
                start += seqlength
            if not (0 <= start < seqlength):
                raise OperationError(self.w_IndexError,
                                     self.wrap("index out of range"))
            stop  = 0
            step  = 0
        return start, stop, step

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
        space.exec_(source.compile(), w_glob, w_glob)
        return space.getitem(w_glob, space.wrap('anonymous'))

## Table describing the regular part of the interface of object spaces,
## namely all methods which only take w_ arguments and return a w_ result
## (if any).  Note: keep in sync with pypy.objspace.flow.operation.Table.

ObjSpace.MethodTable = [
# method name # symbol # number of arguments # special method name(s)
    ('is_',             'is',        2, []),
    ('id',              'id',        1, []),
    ('type',            'type',      1, []),
    ('issubtype',       'issubtype', 2, []),  # not for old-style classes
    ('repr',            'repr',      1, ['__repr__']),
    ('str',             'str',       1, ['__str__']),
    ('len',             'len',       1, ['__len__']),
    ('hash',            'hash',      1, ['__hash__']),
    ('getattr',         'getattr',   2, ['__getattribute__']),
    ('setattr',         'setattr',   3, ['__setattr__']),
    ('delattr',         'delattr',   2, ['__delattr__']),
    ('getitem',         'getitem',   2, ['__getitem__']),
    ('setitem',         'setitem',   3, ['__setitem__']),
    ('delitem',         'delitem',   2, ['__delitem__']),
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
#                 newstring([w_1, w_2,...]) -> w_string from ascii numbers (bytes)
#                  newunicode([i1, i2,...]) -> w_unicode from integers
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
    'unichars_w',
    'interpclass_w',
    'unwrap',
    'is_true',
    'is_w',
    'newtuple',
    'newlist',
    'newstring',
    'newunicode',
    'newdict',
    'newslice',
    'call_args',
    'marshal_w',
    'log',
    ]

