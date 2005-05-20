"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)

"""

import types, sys, md5, os

NoneNotWrapped = object()

from pypy.tool.sourcetools import func_with_new_name
from pypy.interpreter.error import OperationError 
from pypy.interpreter import eval
from pypy.interpreter.function import Function, Method
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, BaseWrappable
from pypy.interpreter.baseobjspace import Wrappable, SpaceCache
from pypy.interpreter.argument import Arguments
from pypy.tool.sourcetools import NiceCompile, compile2

# internal non-translatable parts: 
import py

class Signature:
    "NOT_RPYTHON"
    def __init__(self, func=None, argnames=None, varargname=None,
                 kwargname=None, name = None):
        self.func = func
        if func is not None:
            self.name = func.__name__
        else:
            self.name = name
        if argnames is None:
            argnames = []
        self.argnames = argnames
        self.varargname = varargname
        self.kwargname = kwargname

    def next_arg(self):
        return self._argiter.next()

    def append(self, argname):
        self.argnames.append(argname)

    def signature(self):
        return self.argnames, self.varargname, self.kwargname

    def apply_unwrap_spec(self, unwrap_spec, recipe, new_sig):
        self._argiter = iter(self.argnames)
        for el in unwrap_spec:
            recipe(el, self, new_sig)
        return new_sig


class UnwrapSpecRecipe:
    "NOT_RPYTHON"

    bases_order = [BaseWrappable, W_Root, ObjSpace, Arguments, object]

    def dispatch(self, meth_family, el, orig_sig, new_sig):
        if isinstance(el, str):
            getattr(self, "%s_%s" % (meth_family, el))(el, orig_sig, new_sig)
        elif isinstance(el, tuple):
            getattr(self, "%s_%s" % (meth_family, 'function'))(el, orig_sig, new_sig)
        else:
            for typ in self.bases_order:
                if issubclass(el, typ):
                    getattr(self, "%s__%s" % (meth_family, typ.__name__))(el, orig_sig, new_sig)
                    break
            else:
                assert False, "no match for unwrap_spec element: %s" % el

    def check(self, el, orig_sig, new_sig):
        self.dispatch("check", el, orig_sig, new_sig)

    def emit(self, el, orig_sig, new_sig):
        self.dispatch("emit", el, orig_sig, new_sig)


    # checks for checking interp2app func argument names wrt unwrap_spec
    # and synthetizing an app-level signature

    def check_function(self, (func, cls), orig_sig, app_sig):
        self.check(cls, orig_sig, app_sig)
        
    def check__BaseWrappable(self, el, orig_sig, app_sig):
        name = el.__name__
        argname = orig_sig.next_arg()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r should "
            "not start with 'w_'" % (name, argname, orig_sig.func))
        app_sig.append(argname)
        
    def check__ObjSpace(self, el, orig_sig, app_sig):
        orig_sig.next_arg()

    def check__W_Root(self, el, orig_sig, app_sig):
        assert el is W_Root, "oops"
        argname = orig_sig.next_arg()
        assert argname.startswith('w_'), (
            "argument %s of built-in function %r should "
            "start with 'w_'" % (argname, orig_sig.func))
        app_sig.append(argname[2:])

    def check__Arguments(self, el, orig_sig, app_sig):
        argname = orig_sig.next_arg()
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % orig_sig.func)
        app_sig.varargname = 'args'
        app_sig.kwargname = 'keywords'

    def check_starargs(self, el, orig_sig, app_sig):
        varargname = orig_sig.varargname
        assert varargname.endswith('_w'), (
            "argument *%s of built-in function %r should end in '_w'" %
            (varargname, orig_sig.func))
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % orig_sig.func)
        app_sig.varargname = varargname[:-2]

    def check_args_w(self, el, orig_sig, app_sig):
        argname = orig_sig.next_arg()
        assert argname.endswith('_w'), (
            "rest arguments arg %s of built-in function %r should end in '_w'" %
            (argname, orig_sig.func))
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % orig_sig.func)
        app_sig.varargname = argname[:-2]    

    def check_w_args(self, el, orig_sig, app_sig):
        argname = orig_sig.next_arg()
        assert argname.startswith('w_'), (
            "rest arguments arg %s of built-in function %r should start 'w_'" %
            (argname, orig_sig.func))
        assert app_sig.varargname is None,(
            "built-in function %r has conflicting rest args specs" % orig_sig.func)
        app_sig.varargname = argname[2:]

    def check__object(self, el, orig_sig, app_sig):
        if el not in (int, str, float):
            assert False, "unsupported basic type in uwnrap_spec"
        name = el.__name__
        argname = orig_sig.next_arg()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r should "
            "not start with 'w_'" % (name, argname, orig_sig.func))
        app_sig.append(argname)        

    # collect code to emit for interp2app builtin frames based on unwrap_spec

    def emit_function(self, (func, cls), orig_sig, emit_sig):
        name = func.__name__
        cur = emit_sig.through_scope_w
        emit_sig.setfastscope.append(
            "obj = %s(scope_w[%d])" % (name, cur))
        emit_sig.miniglobals[name] = func
        emit_sig.setfastscope.append(
            "self.%s_arg%d = obj" % (name,cur))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.%s_arg%d" % (name,cur))

    def emit__BaseWrappable(self, el, orig_sig, emit_sig):
        name = el.__name__
        cur = emit_sig.through_scope_w
        emit_sig.setfastscope.append(
            "obj = self.space.interpclass_w(scope_w[%d])" % cur)
        emit_sig.setfastscope.append(
            "if obj is None or not isinstance(obj, %s):" % name)
        emit_sig.setfastscope.append(
            "    raise OperationError(self.space.w_TypeError,self.space.wrap('expected %%s' %% %s.typedef.name ))" % name) # xxx
        emit_sig.miniglobals[name] = el
        emit_sig.miniglobals['OperationError'] = OperationError
        emit_sig.setfastscope.append(
            "self.%s_arg%d = obj" % (name,cur))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.%s_arg%d" % (name,cur))

    def emit__ObjSpace(self, el, orig_sig, emit_sig):
        emit_sig.run_args.append('self.space')

    def emit__W_Root(self, el, orig_sig, emit_sig):
        cur = emit_sig.through_scope_w
        emit_sig.setfastscope.append(
            "self.w_arg%d = scope_w[%d]" % (cur,cur))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.w_arg%d" % cur)

    def emit__Arguments(self, el, orig_sig, emit_sig):
        cur = emit_sig.through_scope_w
        emit_sig.through_scope_w += 2
        emit_sig.miniglobals['Arguments'] = Arguments
        emit_sig.setfastscope.append(
            "self.arguments_arg = "
            "Arguments.frompacked(self.space,scope_w[%d],scope_w[%d])"
                % (cur, cur+1))
        emit_sig.run_args.append("self.arguments_arg")

    def emit_starargs(self, el, orig_sig, emit_sig):
        emit_sig.setfastscope.append(
            "self.starargs_arg_w = self.space.unpacktuple(scope_w[%d])" %
                (emit_sig.through_scope_w))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("*self.starargs_arg_w")

    def emit_args_w(self, el, orig_sig, emit_sig):
        emit_sig.setfastscope.append(
            "self.args_w = self.space.unpacktuple(scope_w[%d])" %
                 (emit_sig.through_scope_w))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.args_w")

    def emit_w_args(self, el, orig_sig, emit_sig):
        cur = emit_sig.through_scope_w
        emit_sig.setfastscope.append(
            "self.w_args = scope_w[%d]" % cur)
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.w_args")

    def emit__object(self, el, orig_sig, emit_sig):
        if el not in (int, str, float):
            assert False, "unsupported basic type in uwnrap_spec"
        name = el.__name__
        cur = emit_sig.through_scope_w
        emit_sig.setfastscope.append(
            "self.%s_arg%d = self.space.%s_w(scope_w[%d])" %
                (name,cur,name,cur))
        emit_sig.through_scope_w += 1
        emit_sig.run_args.append("self.%s_arg%d" % (name,cur))

class BuiltinFrame(eval.Frame):
    "Frame emulation for BuiltinCode."
    # Subclasses of this are defined with the function to delegate to attached through miniglobals.
    # Initialization of locals is already done by the time run() is called,
    # via the interface defined in eval.Frame.

    def setfastscope(self, scope_w):
        """Subclasses with behavior specific for an unwrap spec are generated"""
        raise TypeError, "abstract"

    def getfastscope(self):
        raise OperationError(self.space.w_TypeError,
            self.space.wrap("cannot get fastscope of a BuiltinFrame"))

    def run(self):
        try:
            w_result = self._run()
        except KeyboardInterrupt: 
            raise OperationError(self.space.w_KeyboardInterrupt, self.space.w_None) 
        except MemoryError: 
            raise OperationError(self.space.w_MemoryError, self.space.w_None) 
        except RuntimeError, e: 
            raise OperationError(self.space.w_RuntimeError, 
                                 self.space.wrap("internal error: " + str(e))) 
        if w_result is None:
            w_result = self.space.w_None
        return w_result

    def _run(self):
        """Subclasses with behavior specific for an unwrap spec are generated"""
        raise TypeError, "abstract"

class FuncBox(object):
    pass

class BuiltinCodeSignature(Signature):
    "NOT_RPYTHON"

    def __init__(self,*args,**kwds):
        self.unwrap_spec = kwds.get('unwrap_spec')
        del kwds['unwrap_spec']
        Signature.__init__(self,*args,**kwds)
        self.setfastscope = []
        self.run_args = []
        self.through_scope_w = 0
        self.miniglobals = {}

    def _make_unwrap_frame_class(self, cache={}):
        try:
            key = tuple(self.unwrap_spec)
            frame_cls, box_cls,  run_args = cache[key]
            assert run_args == self.run_args,"unexpected: same spec, different run_args"
            return frame_cls, box_cls
        except KeyError:
            parts = []          
            for el in self.unwrap_spec:
                if isinstance(el, tuple):
                    parts.append(''.join([getattr(subel, '__name__', subel) for subel in el]))
                else:
                    parts.append(getattr(el, '__name__', el))
            label = '_'.join(parts)
            #print label
            setfastscope = self.setfastscope
            if not setfastscope:
                setfastscope = ["pass"]
            setfastscope = ["def setfastscope_UWS_%s(self, scope_w):" % label,
                            #"print 'ENTER',self.code.func.__name__",
                            #"print scope_w"
                            ] + setfastscope
            setfastscope = '\n  '.join(setfastscope)
            # Python 2.2 SyntaxError without newline: Bug #501622
            setfastscope += '\n'
            d = {}
            exec compile2(setfastscope) in self.miniglobals, d
            d['setfastscope'] = d['setfastscope_UWS_%s' % label]
            del d['setfastscope_UWS_%s' % label]

            self.miniglobals['OperationError'] = OperationError
            source = """if 1: 
                def _run_UWS_%s(self):
                    return self.box.func(%s)
                \n""" % (label, ','.join(self.run_args))
            exec compile2(source) in self.miniglobals, d
            d['_run'] = d['_run_UWS_%s' % label]
            del d['_run_UWS_%s' % label]
            frame_cls = type("BuiltinFrame_UWS_%s" % label, (BuiltinFrame,), d)
            box_cls = type("FuncBox_UWS_%s" % label, (FuncBox,), {})
            cache[key] = frame_cls, box_cls, self.run_args
            return frame_cls, box_cls

    def make_frame_class(self, func, cache={}):
        frame_uw_cls, box_cls = self._make_unwrap_frame_class()
        box = box_cls()
        box.func = func
        return type("BuiltinFrame_for_%s" % self.name,
                    (frame_uw_cls,),{'box': box})
        
def make_builtin_frame_class(func, orig_sig, unwrap_spec):
    "NOT_RPYTHON"
    name = (getattr(func, '__module__', None) or '')+'_'+func.__name__
    emit_sig = orig_sig.apply_unwrap_spec(unwrap_spec, UnwrapSpecRecipe().emit,
                                              BuiltinCodeSignature(name=name, unwrap_spec=unwrap_spec))
    cls = emit_sig.make_frame_class(func)
    return cls



class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func, unwrap_spec = None, self_type = None):
        "NOT_RPYTHON"
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.docstring = func.__doc__

        # unwrap_spec can be passed to interp2app or
        # attached as an attribute to the function.
        # It is a list of types or singleton objects:
        #  baseobjspace.ObjSpace is used to specify the space argument
        #  baseobjspace.W_Root is for wrapped arguments to keep wrapped
        #  baseobjspace.BaseWrappable subclasses imply interpclass_w and a typecheck
        #  argument.Arguments is for a final rest arguments Arguments object
        # 'args_w' for unpacktuple applied to rest arguments
        # 'w_args' for rest arguments passed as wrapped tuple
        # str,int,float: unwrap argument as such type
        # (function, cls) use function to check/unwrap argument of type cls
        
        # First extract the signature from the (CPython-level) code object
        from pypy.interpreter import pycode
        argnames, varargname, kwargname = pycode.cpython_code_signature(func.func_code)

        if unwrap_spec is None:
            unwrap_spec = getattr(func,'unwrap_spec',None)

        if unwrap_spec is None:
            unwrap_spec = [ObjSpace]+ [W_Root] * (len(argnames)-1)

            if self_type:
                unwrap_spec = ['self'] + unwrap_spec[1:]
            
        if self_type:
            assert unwrap_spec[0] == 'self',"self_type without 'self' spec element"
            unwrap_spec = list(unwrap_spec)
            unwrap_spec[0] = self_type

        orig_sig = Signature(func, argnames, varargname, kwargname)

        app_sig = orig_sig.apply_unwrap_spec(unwrap_spec, UnwrapSpecRecipe().check,
                                             Signature(func))

        self.sig = argnames, varargname, kwargname = app_sig.signature()

        self.minargs = len(argnames)
        if varargname:
            self.maxargs = sys.maxint
        else:
            self.maxargs = self.minargs

        self.framecls = make_builtin_frame_class(func, orig_sig, unwrap_spec)

    def create_frame(self, space, w_globals, closure=None):
        return self.framecls(space, self, w_globals)

    def signature(self):
        return self.sig

    def getdocstring(self):
        return self.docstring


class interp2app(Wrappable):
    """Build a gateway that calls 'f' at interp-level."""

    # NOTICE interp2app defaults are stored and passed as
    # wrapped values, this to avoid having scope_w be of mixed
    # wrapped and unwrapped types;
    # an exception is made for the NoneNotWrapped special value
    # which is passed around as default as an unwrapped None,
    # unwrapped None and wrapped types are compatible
    #
    # Takes optionally an unwrap_spec, see BuiltinCode

    NOT_RPYTHON_ATTRIBUTES = ['_staticdefs']
    
    def __init__(self, f, app_name=None, unwrap_spec = None):
        "NOT_RPYTHON"
        Wrappable.__init__(self)
        # f must be a function whose name does NOT start with 'app_'
        self_type = None
        if hasattr(f, 'im_func'):
            self_type = f.im_class
            f = f.im_func
        if not isinstance(f, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % f
        if app_name is None:
            if f.func_name.startswith('app_'):
                raise ValueError, ("function name %r suspiciously starts "
                                   "with 'app_'" % f.func_name)
            app_name = f.func_name
        self._code = BuiltinCode(f, unwrap_spec=unwrap_spec, self_type = self_type)
        self.__name__ = f.func_name
        self.name = app_name
        self._staticdefs = list(f.func_defaults or ())

    def _getdefaults(self, space):
        "NOT_RPYTHON"
        defs_w = []
        for val in self._staticdefs:
            if val is NoneNotWrapped:
                defs_w.append(None)
            else:
                defs_w.append(space.wrap(val))
        return defs_w

    # lazy binding to space

    def __spacebind__(self, space):
        # we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return self.get_function(space)

    def get_function(self, space):
        return self.getcache(space).getorbuild(self)

    def getcache(self, space):
        return space.fromcache(GatewayCache)

    def get_method(self, obj):
        # to bind this as a method out of an instance, we build a
        # Function and get it.
        # the object space is implicitely fetched out of the instance
        assert self._code.ismethod, (
            'global built-in function %r used as method' %
            self._code.func)

        space = obj.space
        fn = self.get_function(space)
        w_obj = space.wrap(obj)
        return Method(space, space.wrap(fn),
                      w_obj, space.type(w_obj))


class GatewayCache(SpaceCache):
    def build(cache, gateway):
        "NOT_RPYTHON"
        space = cache.space
        defs = gateway._getdefaults(space) # needs to be implemented by subclass
        code = gateway._code
        fn = Function(space, code, None, defs, forcename = gateway.name)
        return fn


# 
# the next gateways are to be used only for 
# temporary/initialization purposes 
     
class interp2app_temp(interp2app): 
    "NOT_RPYTHON"
    def getcache(self, space): 
        return self.__dict__.setdefault(space, GatewayCache(space))


# and now for something completely different ... 
#

class ApplevelClass:
    """A container for app-level source code that should be executed
    as a module in the object space;  interphook() builds a static
    interp-level function that invokes the callable with the given
    name at app-level."""

    hidden_applevel = True
    use_geninterp = True    # change this to disable geninterp globally

    def __init__(self, source, filename = None, modname = '__builtin__'):
        self.filename = filename
        self.source = source
        self.modname = modname
        # look at the first three lines for a NOT_RPYTHON tag
        first = "\n".join(source.split("\n", 3)[:3])
        self.use_geninterp = "NOT_RPYTHON" not in first

    def getwdict(self, space):
        return space.fromcache(ApplevelCache).getorbuild(self)

    def buildmodule(self, space, name='applevel'):
        from pypy.interpreter.module import Module
        return Module(space, space.wrap(name), self.getwdict(space))

    def wget(self, space, name): 
        w_globals = self.getwdict(space) 
        return space.getitem(w_globals, space.wrap(name))

    def interphook(self, name):
        "NOT_RPYTHON"
        def appcaller(space, *args_w):
            if not isinstance(space, ObjSpace): 
                raise TypeError("first argument must be a space instance.")
            # redirect if the space handles this specially  XXX can this be factored a bit less flow space dependetly
            if hasattr(space, 'specialcases'):
                sc = space.specialcases
                if ApplevelClass in sc:
                    ret_w = sc[ApplevelClass](space, self, name, args_w)
                    if ret_w is not None: # it was RPython
                        return ret_w
            args = Arguments(space, list(args_w))
            w_func = self.wget(space, name) 
            return space.call_args(w_func, args)
        def get_function(space):
            w_func = self.wget(space, name) 
            return space.unwrap(w_func)
        appcaller = func_with_new_name(appcaller, name)
        appcaller.get_function = get_function
        return appcaller

    def _freeze_(self):
        return True  # hint for the annotator: applevel instances are constants


class ApplevelCache(SpaceCache):
    """The cache mapping each applevel instance to its lazily built w_dict"""

    def build(self, app):
        "NOT_RPYTHON.  Called indirectly by Applevel.getwdict()."
        if app.use_geninterp:
            return PyPyCacheDir.build_applevelinterp_dict(app, self.space)
        else:
            return build_applevel_dict(app, self.space)


# __________ pure applevel version __________

def build_applevel_dict(self, space):
    "NOT_RPYTHON"
    if self.filename is None:
        code = py.code.Source(self.source).compile()
    else:
        code = NiceCompile(self.filename)(self.source)

    from pypy.interpreter.pycode import PyCode
    pycode = PyCode(space)._from_code(code, hidden_applevel=self.hidden_applevel)
    w_glob = space.newdict([])
    space.setitem(w_glob, space.wrap('__name__'), space.wrap('__builtin__'))
    space.exec_(pycode, w_glob, w_glob)
    return w_glob

# __________ geninterplevel version __________

class PyPyCacheDir:
    # similar to applevel, but using translation to interp-level.
    # This version maintains a cache folder with single files.

    def build_applevelinterp_dict(cls, self, space):
        "NOT_RPYTHON"
        # N.B. 'self' is the ApplevelInterp; this is a class method,
        # just so that we have a convenient place to store the global state.
        if not cls._setup_done:
            cls._setup()

        from pypy.translator.geninterplevel import translate_as_module
        scramble = md5.new(cls.seed)
        scramble.update(self.source)
        key = scramble.hexdigest()
        initfunc = cls.known_source.get(key)
        if not initfunc:
            # try to get it from file
            name = key
            if self.filename:
                prename = os.path.splitext(os.path.basename(self.filename))[0]
            else:
                prename = 'zznoname'
            name = "%s_%s" % (prename, name)
            try:
                __import__("pypy._cache."+name)
            except ImportError, x:
                # print x
                pass
            else:
                initfunc = cls.known_source[key]
        if not initfunc:
            # build it and put it into a file
            initfunc, newsrc = translate_as_module(
                self.source, self.filename, self.modname)
            fname = cls.cache_path.join(name+".py").strpath
            f = file(fname, "w")
            print >> f, """\
# self-destruct on double-click:
if __name__ == "__main__":
    from pypy import _cache
    import os
    namestart = os.path.join(os.path.split(_cache.__file__)[0], '%s')
    for ending in ('.py', '.pyc', '.pyo'):
        try:
            os.unlink(namestart+ending)
        except os.error:
            pass""" % name
            print >> f
            print >> f, newsrc
            print >> f, "from pypy._cache import known_source"
            print >> f, "known_source[%r] = %s" % (key, initfunc.__name__)
        w_glob = initfunc(space)
        return w_glob
    build_applevelinterp_dict = classmethod(build_applevelinterp_dict)

    _setup_done = False

    def _setup(cls):
        """NOT_RPYTHON"""
        lp = py.path.local
        import pypy, os
        p = lp(pypy.__file__).new(basename='_cache').ensure(dir=1)
        cls.cache_path = p
        ini = p.join('__init__.py')
        try:
            if not ini.check():
                raise ImportError  # don't import if only a .pyc file left!!!
            from pypy._cache import known_source, \
                 GI_VERSION_RENDERED
        except ImportError:
            GI_VERSION_RENDERED = 0
        from pypy.translator.geninterplevel import GI_VERSION
        cls.seed = md5.new(str(GI_VERSION)).digest()
        if GI_VERSION != GI_VERSION_RENDERED or GI_VERSION is None:
            for pth in p.listdir():
                try:
                    pth.remove()
                except: pass
            file(str(ini), "w").write("""\
# This folder acts as a cache for code snippets which have been
# compiled by compile_as_module().
# It will get a new entry for every piece of code that has
# not been seen, yet.
#
# Caution! Only the code snippet is checked. If something
# is imported, changes are not detected. Also, changes
# to geninterplevel or gateway are also not checked.
# Exception: There is a checked version number in geninterplevel.py
#
# If in doubt, remove this file from time to time.

GI_VERSION_RENDERED = %r

known_source = {}

# self-destruct on double-click:
def harakiri():
    import pypy._cache as _c
    import py
    lp = py.path.local
    for pth in lp(_c.__file__).dirpath().listdir():
        try:
            pth.remove()
        except: pass

if __name__ == "__main__":
    harakiri()

del harakiri
""" % GI_VERSION)
        import pypy._cache
        cls.known_source = pypy._cache.known_source
        cls._setup_done = True
    _setup = classmethod(_setup)

# ____________________________________________________________

def appdef(source, applevel=ApplevelClass):
    """ NOT_RPYTHON: build an app-level helper function, like for example:
    myfunc = appdef('''myfunc(x, y):
                           return x+y
                    ''')
    """ 
    from pypy.interpreter.pycode import PyCode
    if not isinstance(source, str): 
        source = str(py.code.Source(source).strip())
        assert source.startswith("def "), "can only transform functions" 
        source = source[4:]
    p = source.find('(')
    assert p >= 0
    funcname = source[:p].strip()
    source = source[p:]
    return applevel("def %s%s\n" % (funcname, source)).interphook(funcname)

applevel = ApplevelClass   # backward compatibility
app2interp = appdef   # backward compatibility


class applevel_temp(ApplevelClass):
    hidden_applevel = False
    def getwdict(self, space):    # no cache
        return build_applevel_dict(self, space)

if ApplevelClass.use_geninterp:
    class applevelinterp_temp(ApplevelClass):
        hidden_applevel = False
        def getwdict(self, space):   # no cache
            return PyPyCacheDir.build_applevelinterp_dict(self, space)
else:
    applevelinterp_temp = applevel_temp

# app2interp_temp is used for testing mainly
def app2interp_temp(func, applevel_temp=applevel_temp):
    """ NOT_RPYTHON """
    return appdef(func, applevel_temp)
