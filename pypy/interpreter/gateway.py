"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* Gateway     (a space-independent gateway to a Code object)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)
* exportall   (mass-call interp2app on a whole dict of objects)
* importall   (mass-call app2interp on a whole dict of objects)

"""

import types, sys

from pypy.tool import hack
from pypy.interpreter.error import OperationError 
from pypy.interpreter import eval, pycode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.baseobjspace import W_Root,ObjSpace,Wrappable
from pypy.interpreter.argument import Arguments
from pypy.tool.cache import Cache 

class Signature:
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
        self.rewind()

    def rewind(self):
        self._iter = iter(self.argnames)
        
    def __iter__(self):
        return self

    def next(self):
        return self._iter.next()

    def append(self, argname):
        self.argnames.append(argname)

    def signature(self):
        return self.argnames, self.varargname, self.kwargname

def apply_unwrap_spec(unwrap_spec, orig_sig, new_sig, recipes):
    for el in unwrap_spec:
        recipes[el](orig_sig, new_sig)
    return new_sig


class BuiltinCodeSignature(Signature):

    def __init__(self,*args,**kwds):
        Signature.__init__(self,*args,**kwds)
        self.setfastscope = []
        self.run_args = []
        self.through_scope_w = 0

    def make_frame_class(self):
        setfastscope = self.setfastscope
        if not setfastscope:
            setfastscope = ["pass"]
        setfastscope = ["def setfastscope(self, scope_w):",
                        #"print 'ENTER',self.code.func.__name__",
                        #"print scope_w"
                        ] + setfastscope
        setfastscope = '\n  '.join(setfastscope)
        d = {}
        exec setfastscope in globals(),d
        exec """
def run(self):
    w_result = self.code.func(%s)
    if w_result is None:
        w_result = self.space.w_None
    return w_result
""" % ','.join(self.run_args) in globals(),d
        return type("BuiltinFrame_for_%s" % self.name,
                    (BuiltinFrame,),d)
        
    
def unwrap_spec_check_space(orig_sig, new_sig):
    orig_sig.next()
    
def unwrap_spec_check_self(orig_sig, new_sig):
    argname = orig_sig.next()
    new_sig.append(argname)
        
        
def unwrap_spec_check_wrapped(orig_sig, new_sig):
    argname = orig_sig.next()
    assert argname.startswith('w_'), (
        "argument %s of built-in function %r should "
        "start with 'w_'" % (argname, orig_sig.func))
    new_sig.append(argname[2:])

def unwrap_spec_check_arguments(orig_sig, new_sig):
    argname = orig_sig.next()
    assert new_sig.varargname is None,(
        "built-in function %r has conflicting rest args specs" % orig_sig.func)
    new_sig.varargname = 'args'
    new_sig.kwargname = 'keywords'
        
def unwrap_spec_check_starargs(orig_sig, new_sig):
    varargname = orig_sig.varargname
    assert varargname.endswith('_w'), (
        "argument *%s of built-in function %r should end in '_w'" %
        (varargname, orig_sig.func))
    assert new_sig.varargname is None,(
        "built-in function %r has conflicting rest args specs" % orig_sig.func)
    new_sig.varargname = varargname[:-2]

def unwrap_spec_check_args_w(orig_sig, new_sig):
    argname = orig_sig.next()
    assert argname.endswith('_w'), (
        "rest arguments arg %s of built-in function %r should end in '_w'" %
        (argname, orig_sig.func))
    assert new_sig.varargname is None,(
        "built-in function %r has conflicting rest args specs" % orig_sig.func)
    new_sig.varargname = argname[:-2]
        
# recipes for checking interp2app func argumes wrt unwrap_spec
unwrap_spec_checks = {
    ObjSpace: unwrap_spec_check_space,
    'self': unwrap_spec_check_self,
    W_Root: unwrap_spec_check_wrapped,
    Arguments: unwrap_spec_check_arguments,
    '*': unwrap_spec_check_starargs,
    'args_w': unwrap_spec_check_args_w,
}

def unwrap_spec_emit_space(orig_sig, new_sig):
    new_sig.run_args.append('self.space')
    
def unwrap_spec_emit_self(orig_sig, new_sig):
    new_sig.setfastscope.append(
        "self.self_arg = self.space.interpclass_w(scope_w[%d])" %
            (new_sig.through_scope_w))
    new_sig.through_scope_w += 1
    new_sig.run_args.append("self.self_arg")
        
def unwrap_spec_emit_wrapped(orig_sig, new_sig):
    cur = new_sig.through_scope_w
    new_sig.setfastscope.append(
        "self.w_arg%d = scope_w[%d]" % (cur,cur))
    new_sig.through_scope_w += 1
    new_sig.run_args.append("self.w_arg%d" % cur)


def unwrap_spec_emit_arguments(orig_sig, new_sig):
    cur = new_sig.through_scope_w
    new_sig.through_scope_w += 2
    new_sig.setfastscope.append(
        "self.arguments_arg = "
        "Arguments.frompacked(self.space,scope_w[%d],scope_w[%d])"
            % (cur, cur+1))
    new_sig.run_args.append("self.arguments_arg")
        
def unwrap_spec_emit_starargs(orig_sig, new_sig):
    new_sig.setfastscope.append(
        "self.starargs_arg_w = self.space.unpacktuple(scope_w[%d])" %
            (new_sig.through_scope_w))
    new_sig.through_scope_w += 1
    new_sig.run_args.append("*self.starargs_arg_w")

def unwrap_spec_emit_args_w(orig_sig, new_sig):
    new_sig.setfastscope.append(
        "self.args_w = self.space.unpacktuple(scope_w[%d])" %
             (new_sig.through_scope_w))
    new_sig.through_scope_w += 1
    new_sig.run_args.append("self.args_w")
        
# recipes for emitting unwrapping code for arguments of a interp2app func
# wrt a unwrap_spec
unwrap_spec_emit = {
    ObjSpace: unwrap_spec_emit_space,
    'self': unwrap_spec_emit_self,
    W_Root: unwrap_spec_emit_wrapped,
    Arguments: unwrap_spec_emit_arguments,
    '*': unwrap_spec_emit_starargs,
    'args_w': unwrap_spec_emit_args_w,
}

# unwrap_spec_check/emit for str,int,float
for basic_type in [str,int,float]:
    name = basic_type.__name__
    def unwrap_spec_check_basic(orig_sig, new_sig, name=name):
        argname = orig_sig.next()
        assert not argname.startswith('w_'), (
            "unwrapped %s argument %s of built-in function %r should "
            "not start with 'w_'" % (name, argname, orig_sig.func))
        new_sig.append(argname)
    def unwrap_spec_emit_basic(orig_sig, new_sig, name=name):
        cur = new_sig.through_scope_w
        new_sig.setfastscope.append(
            "self.%s_arg%d = self.space.%s_w(scope_w[%d])" %
                (name,cur,name,cur))
        new_sig.through_scope_w += 1
        new_sig.run_args.append("self.%s_arg%d" % (name,cur))
    unwrap_spec_checks[basic_type] = hack.func_with_new_name(
        unwrap_spec_check_basic, "unwrap_spec_check_%s" % name)
    unwrap_spec_emit[basic_type] = hack.func_with_new_name(
        unwrap_spec_emit_basic, "unwrap_spec_emit_%s" % name)    
    


def make_builtin_frame_class_for_unwrap_spec(unwrap_spec, cache={}):
    "NOT_RPYTHON"
    key = tuple(unwrap_spec)
    try:
        return cache[key]
    except KeyError:
        name = '_'.join([getattr(k, "__name__", k) for k in key])
        emit_sig = apply_unwrap_spec(unwrap_spec, None,
                                     BuiltinCodeSignature(name=name),
                                     unwrap_spec_emit)

        cache[key] = cls = emit_sig.make_frame_class()
        return cls
    

class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func, ismethod=None, spacearg=None, unwrap_spec = None):
        "NOT_RPYTHON"
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.func = func
        self.docstring = func.__doc__
        # signature-based hacks if unwrap_spec is not specified:
        # renaming arguments from w_xyz to xyz.
        # Currently we enforce the following signature tricks:
        #  * the first arg must be either 'self' or 'space'
        #  * 'w_' prefixes for the rest
        #  * '_w' suffix for the optional '*' argument
        #  * alternatively a final '__args__' means an Arguments()
        # Not exactly a clean approach XXX.
        # --
        # unwrap_spec can be passed to interp2app or
        # attached as an attribute to the function.
        # It is a list of types or singleton objects:
        #  baseobjspace.ObjSpace is used to specify the space argument
        #  'self' is used to specify a self method argument
        #  baseobjspace.W_Root is for wrapped arguments to keep wrapped
        #  argument.Arguments is for a final rest arguments Arguments object
        # 'args_w' for unpacktuple applied rest arguments
        # str,int,float: unwrap argument as such type
        
        # First extract the signature from the (CPython-level) code object
        argnames, varargname, kwargname = pycode.cpython_code_signature(func.func_code)

        if unwrap_spec is None:
            unwrap_spec = getattr(func,'unwrap_spec',None)
        
        if unwrap_spec is None:

            unwrap_spec = []

            argnames = list(argnames)
            lookslikemethod = argnames[:1] == ['self']
            if ismethod is None:
                ismethod = lookslikemethod
            if spacearg is None:
                spacearg = not lookslikemethod
            self.ismethod = ismethod
            self.spacearg = spacearg
            assert kwargname is None, (
                "built-in function %r should not take a ** argument" % func)

            n = len(argnames)

            if self.ismethod:
                unwrap_spec.append('self')
                n -= 1
            if self.spacearg:
                unwrap_spec.append(ObjSpace)
                n -= 1

            self.generalargs = argnames[-1:] == ['__args__']
            self.starargs = varargname is not None

            if self.generalargs:
                unwrap_spec.extend([W_Root] * (n-1))
                unwrap_spec.append(Arguments)
            else:
                unwrap_spec.extend([W_Root] * n)

            if self.starargs:
                unwrap_spec.append('*')
        else:
            assert not ismethod, ("if unwrap_spec is specified, "
                                  "ismethod is not expected")
            assert not spacearg, ("if unwrap_spec is specified, " 
                                  "spacearg is not expected")

        orig_sig = Signature(func, argnames, varargname, kwargname)

        new_sig = apply_unwrap_spec(unwrap_spec, orig_sig,
                                    Signature(func),
                                    unwrap_spec_checks)

        self.sig = argnames, varargname, kwargname = new_sig.signature()

        self.minargs = len(argnames)
        if varargname:
            self.maxargs = sys.maxint
        else:
            self.maxargs = self.minargs

        self.framecls = make_builtin_frame_class_for_unwrap_spec(unwrap_spec)

    def create_frame(self, space, w_globals, closure=None):
        return self.framecls(space, self, w_globals)

    def signature(self):
        return self.sig

    def getdocstring(self):
        return self.docstring


class BuiltinFrame(eval.Frame):
    "Frame emulation for BuiltinCode."
    # This is essentially just a delegation to the 'func' of the BuiltinCode.
    # Initialization of locals is already done by the time run() is called,
    # via the interface defined in eval.Frame.

    def setfastscope(self, scope_w):
        """Subclasses with behavior specific for an unwrap spec are generated"""
        raise TypeError, "abstract"

    def getfastscope(self):
        raise OperationError(self.space.w_TypeError,
            self.space.wrap("cannot get fastscope of a BuiltinFrame"))

    def run(self):
        """Subclasses with behavior specific for an unwrap spec are generated"""
        raise TypeError, "abstract"        


class Gateway(Wrappable):
    """General-purpose utility for the interpreter-level to create callables
    that transparently invoke code objects (and thus possibly interpreted
    app-level code)."""

    # This is similar to a Function object, but not bound to a particular
    # object space. During the call, the object space is either given
    # explicitly as the first argument (for plain function), or is read
    # from 'self.space' for methods.

        # after initialization the following attributes should be set
        #   name
        #   _staticglobals 
        #   _staticdefs
        #
        #  getcode is called lazily to get the code object to construct
        #  the space-bound function

    NOT_RPYTHON_ATTRIBUTES = ['_staticglobals', '_staticdefs']

    def getcode(self, space):
        # needs to be implemented by subclasses
        raise TypeError, "abstract"
        
    def __spacebind__(self, space):
        # to wrap a Gateway, we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return self.get_function(space)

    def get_function(self, space):
        return space.loadfromcache(self, 
                                   Gateway.build_all_functions, 
                                   self.getcache(space))

    def getglobals(self, space):
        "NOT_RPYTHON"
        if self._staticglobals is None:
            w_globals = None
        else:
            # is there another Gateway in _staticglobals for which we
            # already have a w_globals for this space ?
            cache = self.getcache(space) 
            for value in self._staticglobals.itervalues():
                if isinstance(value, Gateway):
                    if value in cache.content: 
                        # yes, we share its w_globals
                        fn = cache.content[value] 
                        w_globals = fn.w_func_globals
                        break
            else:
                # no, we build all Gateways in the _staticglobals now.
                w_globals = build_dict(self._staticglobals, space)
            return w_globals
                
    def build_all_functions(self, space):
        "NOT_RPYTHON"
        # the construction is supposed to be done only once in advance,
        # but must be done lazily when needed only, because
        #   1) it depends on the object space
        #   2) the w_globals must not be built before the underlying
        #      _staticglobals is completely initialized, because
        #      w_globals must be built only once for all the Gateway
        #      instances of _staticglobals
        return self._build_function(space, self.getglobals(space))

    def getcache(self, space):
        return space._gatewaycache 

    def _build_function(self, space, w_globals):
        "NOT_RPYTHON"
        cache = self.getcache(space) 
        try: 
            return cache.content[self] 
        except KeyError: 
            defs = self.getdefaults(space)  # needs to be implemented by subclass
            code = self.getcode(space)
            fn = Function(space, code, w_globals, defs, forcename = self.name)
            cache.content[self] = fn 
            return fn

    def get_method(self, obj):
        # to get the Gateway as a method out of an instance, we build a
        # Function and get it.
        # the object space is implicitely fetched out of the instance
        space = obj.space
        fn = self.get_function(space)
        w_obj = space.wrap(obj)
        return Method(space, space.wrap(fn),
                      w_obj, space.type(w_obj))


class app2interp(Gateway):
    """Build a Gateway that calls 'app' at app-level."""

    NOT_RPYTHON_ATTRIBUTES = ['_staticcode'] + Gateway.NOT_RPYTHON_ATTRIBUTES
    
    def __init__(self, app, app_name=None):
        "NOT_RPYTHON"
        Gateway.__init__(self)
        # app must be a function whose name starts with 'app_'.
        if not isinstance(app, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % app
        if app_name is None:
            if not app.func_name.startswith('app_'):
                raise ValueError, ("function name must start with 'app_'; "
                                   "%r does not" % app.func_name)
            app_name = app.func_name[4:]
        self.name = app_name
        self._staticcode = app.func_code
        self._staticglobals = app.func_globals
        self._staticdefs = list(app.func_defaults or ())

    def getcode(self, space):
        "NOT_RPYTHON"
        code = pycode.PyCode(space)
        code._from_code(self._staticcode)
        return code

    def getdefaults(self, space):
        "NOT_RPYTHON"
        return [space.wrap(val) for val in self._staticdefs]

    def __call__(self, space, *args_w):
        # to call the Gateway as a non-method, 'space' must be explicitly
        # supplied. We build the Function object and call it.
        fn = self.get_function(space)
        return space.call_function(space.wrap(fn), *args_w)

    def __get__(self, obj, cls=None):
        "NOT_RPYTHON"
        if obj is None:
            return self
        else:
            space = obj.space
            w_method = space.wrap(self.get_method(obj))
            def helper_method_caller(*args_w):
                return space.call_function(w_method, *args_w)
            return helper_method_caller

class interp2app(Gateway):
    """Build a Gateway that calls 'f' at interp-level."""

    # NOTICE even interp2app defaults are stored and passed as
    # wrapped values, this to avoid having scope_w be of mixed
    # wrapped and unwrapped types,
    # an exception is made for None which is passed around as default
    # as an unwrapped None, unwrapped None and wrapped types are
    # compatible
    #
    # Takes optionally an unwrap_spec, see BuiltinCode
    
    def __init__(self, f, app_name=None,
                 ismethod=None, spacearg=None, unwrap_spec = None):
        "NOT_RPYTHON"
        Gateway.__init__(self)
        # f must be a function whose name does NOT starts with 'app_'
        if not isinstance(f, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % f
        if app_name is None:
            if f.func_name.startswith('app_'):
                raise ValueError, ("function name %r suspiciously starts "
                                   "with 'app_'" % f.func_name)
            app_name = f.func_name
        self._code = BuiltinCode(f, ismethod=ismethod,
                                  spacearg=spacearg,
                                  unwrap_spec=unwrap_spec)
        self.name = app_name
        self._staticdefs = list(f.func_defaults or ())
        #if self._staticdefs:
        #    print f.__module__,f.__name__,"HAS NON TRIVIAL DEFLS",self._staticdefs
        self._staticglobals = None

    def getcode(self, space):
        return self._code

    def getdefaults(self, space):
        "NOT_RPYTHON"
        defs_w = []
        for val in self._staticdefs:
            if val is None:
                defs_w.append(val)
            else:
                defs_w.append(space.wrap(val))
        return defs_w

    def get_method(self, obj):
       assert self._code.ismethod, (
           'global built-in function %r used as method' %
           self._code.func)
       return Gateway.get_method(self, obj)


def exportall(d, temporary=False):
    """NOT_RPYTHON: Publish every function from a dict."""
    if temporary:
        i2a = interp2app_temp
    else:
        i2a = interp2app
    for name, obj in d.items():
        if isinstance(obj, types.FunctionType):
            # names starting in 'app_' are supposedly already app-level
            if name.startswith('app_'):
                continue
            # ignore tricky functions with another interp-level meaning
            if name in ('__init__', '__new__'):
                continue
            # ignore names in '_xyz'
            if name.startswith('_') and not name.endswith('_'):
                continue
            if 'app_'+name not in d:
                d['app_'+name] = i2a(obj, name)

def export_values(space, dic, w_namespace):
    "NOT_RPYTHON"
    for name, w_value in dic.items():
        if name.startswith('w_'):
            if name == 'w_dict':
                w_name = space.wrap('__dict__')
            elif name == 'w_name':
                w_name = space.wrap('__name__')
            else:
                w_name = space.wrap(name[2:])
            space.setitem(w_namespace, w_name, w_value)

def importall(d, temporary=False):
    """NOT_RPYTHON: Import all app_-level functions as Gateways into a dict."""
    if temporary:
        a2i = app2interp_temp
    else:
        a2i = app2interp
    for name, obj in d.items():
        if name.startswith('app_') and name[4:] not in d:
            if isinstance(obj, types.FunctionType):
                d[name[4:]] = a2i(obj, name[4:])

def build_dict(d, space):
    """NOT_RPYTHON:
    Search all Gateways and put them into a wrapped dictionary."""
    w_globals = space.newdict([])
    for value in d.itervalues():
        if isinstance(value, Gateway):
            fn = value._build_function(space, w_globals)
            w_name = space.wrap(value.name)
            w_object = space.wrap(fn)
            space.setitem(w_globals, w_name, w_object)
    if hasattr(space, 'w_sys'):  # give them 'sys' if it exists already
        space.setitem(w_globals, space.wrap('sys'), space.w_sys)
    return w_globals


# 
# the next gateways are to be used only for 
# temporary/initialization purposes 
class app2interp_temp(app2interp):
    "NOT_RPYTHON"
    def getcache(self, space): 
        return self.__dict__.setdefault(space, Cache())
        #                               ^^^^^
        #                          armin suggested this 
     
class interp2app_temp(interp2app): 
    "NOT_RPYTHON"
    def getcache(self, space): 
        return self.__dict__.setdefault(space, Cache())
