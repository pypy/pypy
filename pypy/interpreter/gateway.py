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
from pypy.interpreter import eval, pycode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments


class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func, ismethod=None, spacearg=None):
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.func = func
        self.docstring = func.__doc__
        # extract the signature from the (CPython-level) code object
        tmp = pycode.PyCode(None)
        tmp._from_code(func.func_code)
        # signature-based hacks: renaming arguments from w_xyz to xyz.
        # Currently we enforce the following signature tricks:
        #  * the first arg must be either 'self' or 'space'
        #  * 'w_' prefixes for the rest
        #  * '_w' suffix for the optional '*' argument
        #  * alternatively a final '__args__' means an Arguments()
        # Not exactly a clean approach XXX.
        argnames, varargname, kwargname = tmp.signature()
        argnames = list(argnames)
        lookslikemethod = argnames[:1] == ['self']
        if ismethod is None:
            ismethod = lookslikemethod
        if spacearg is None:
            spacearg = not lookslikemethod
        self.ismethod = ismethod
        self.spacearg = spacearg
        if spacearg:
            del argnames[0]

        assert kwargname is None, (
            "built-in function %r should not take a ** argument" % func)

        self.generalargs = argnames[-1:] == ['__args__']
        self.starargs = varargname is not None
        assert not (self.generalargs and self.starargs), (
            "built-in function %r has both __args__ and a * argument" % func)
        if self.generalargs:
            del argnames[-1]
            varargname = "args"
            kwargname = "keywords"
        elif self.starargs:
            assert varargname.endswith('_w'), (
                "argument *%s of built-in function %r should end in '_w'" %
                (varargname, func))
            varargname = varargname[:-2]

        for i in range(ismethod, len(argnames)):
            a = argnames[i]
            assert a.startswith('w_'), (
                "argument %s of built-in function %r should "
                "start with 'w_'" % (a, func))
            argnames[i] = a[2:]

        self.sig = argnames, varargname, kwargname
        self.minargs = len(argnames)
        if self.starargs:
            self.maxargs = sys.maxint
        else:
            self.maxargs = self.minargs

    def create_frame(self, space, w_globals, closure=None):
        return BuiltinFrame(space, self, w_globals)

    def signature(self):
        return self.sig

    def getdocstring(self):
        return self.docstring

    def performance_shortcut_call(self, space, args):
        # this shortcut is only used for performance reasons
        if self.generalargs or args.kwds_w:
            return None
        args_w = args.args_w
        if not (self.minargs <= len(args_w) <= self.maxargs):
            return None
        if self.ismethod:
            if not args_w:
                return None
            args_w = list(args_w)
            args_w[0] = space.unwrap(args_w[0])
        if self.spacearg:
            w_result = self.func(space, *args_w)
        else:
            w_result = self.func(*args_w)
        if w_result is None:
            w_result = space.w_None
        return w_result

    def performance_shortcut_call_meth(self, space, w_obj, args):
        # this shortcut is only used for performance reasons
        if self.generalargs:
            if self.ismethod and not self.spacearg and len(self.sig[0]) == 1:
                w_result = self.func(space.unwrap(w_obj), args)
            else:
                return None
        else:
            if args.kwds_w:
                return None
            if not (self.minargs <= 1+len(args.args_w) <= self.maxargs):
                return None
            if self.ismethod:
                w_obj = space.unwrap(w_obj) # abuse name w_obj
            if self.spacearg:
                w_result = self.func(space, w_obj, *args.args_w)
            else:
                w_result = self.func(w_obj, *args.args_w)
        if w_result is None:
            w_result = space.w_None
        return w_result


class BuiltinFrame(eval.Frame):
    "Frame emulation for BuiltinCode."
    # This is essentially just a delegation to the 'func' of the BuiltinCode.
    # Initialization of locals is already done by the time run() is called,
    # via the interface defined in eval.Frame.

    def run(self):
        argarray = list(self.fastlocals_w)
        if self.code.generalargs:
            w_kwds = argarray.pop()
            w_args = argarray.pop()
            argarray.append(Arguments.frompacked(self.space, w_args, w_kwds))
        elif self.code.starargs:
            w_args = argarray.pop()
            argarray += self.space.unpacktuple(w_args)
        if self.code.ismethod:
            argarray[0] = self.space.unwrap(argarray[0])
        if self.code.spacearg:
            w_result = self.code.func(self.space, *argarray)
        else:
            w_result = self.code.func(*argarray)
        if w_result is None:
            w_result = self.space.w_None
        return w_result


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
        #   code 
        #   staticglobals 
        #   staticdefs 

    def __spacebind__(self, space):
        # to wrap a Gateway, we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return self.get_function(space)

    def get_function(self, space):
        return space.loadfromcache(self, 
                                   Gateway.build_all_functions, 
                                   self.getcache(space))

    def build_all_functions(self, space):
        # the construction is supposed to be done only once in advance,
        # but must be done lazily when needed only, because
        #   1) it depends on the object space
        #   2) the w_globals must not be built before the underlying
        #      staticglobals is completely initialized, because
        #      w_globals must be built only once for all the Gateway
        #      instances of staticglobals
        if self.staticglobals is None:
            w_globals = None
        else:
            # is there another Gateway in staticglobals for which we
            # already have a w_globals for this space ?
            cache = self.getcache(space) 
            for value in self.staticglobals.itervalues():
                if isinstance(value, Gateway):
                    if value in cache: 
                        # yes, we share its w_globals
                        fn = cache[value] 
                        w_globals = fn.w_func_globals
                        break
            else:
                # no, we build all Gateways in the staticglobals now.
                w_globals = build_dict(self.staticglobals, space)
        return self._build_function(space, w_globals)

    def getcache(self, space):
        return space._gatewaycache 

    def _build_function(self, space, w_globals):
        cache = self.getcache(space) 
        try: 
            return cache[self] 
        except KeyError: 
            defs = self.getdefaults(space)  # needs to be implemented by subclass
            fn = Function(space, self.code, w_globals, defs, forcename = self.name)
            cache[self] = fn 
            return fn

    def get_method(self, obj):
        # to get the Gateway as a method out of an instance, we build a
        # Function and get it.
        # the object space is implicitely fetched out of the instance
        if isinstance(self.code, BuiltinCode):
            assert self.code.ismethod, (
                'global built-in function %r used as method' %
                self.code.func)
        space = obj.space
        fn = self.get_function(space)
        w_obj = space.wrap(obj)
        return Method(space, space.wrap(fn),
                      w_obj, space.type(w_obj)) 


class app2interp(Gateway):
    """Build a Gateway that calls 'app' at app-level."""
    def __init__(self, app, app_name=None):
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
        self.code = pycode.PyCode(None)
        self.code._from_code(app.func_code)
        self.staticglobals = app.func_globals
        self.staticdefs = list(app.func_defaults or ())

    def getdefaults(self, space):
        return [space.wrap(val) for val in self.staticdefs]

    def __call__(self, space, *args_w):
        # to call the Gateway as a non-method, 'space' must be explicitly
        # supplied. We build the Function object and call it.
        fn = self.get_function(space)
        return space.call_function(space.wrap(fn), *args_w)

    def __get__(self, obj, cls=None):
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
    def __init__(self, f, app_name=None):
        Gateway.__init__(self)
        # f must be a function whose name does NOT starts with 'app_'
        if not isinstance(f, types.FunctionType):
            raise TypeError, "function expected, got %r instead" % f
        if app_name is None:
            if f.func_name.startswith('app_'):
                raise ValueError, ("function name %r suspiciously starts "
                                   "with 'app_'" % f.func_name)
            app_name = f.func_name
        self.code = BuiltinCode(f)
        self.name = app_name
        self.staticdefs = list(f.func_defaults or ())
        self.staticglobals = None

    def getdefaults(self, space):
        return self.staticdefs

def exportall(d, temporary=False):
    """Publish every function from a dict."""
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
    """Import all app_-level functions as Gateways into a dict."""
    if temporary:
        a2i = app2interp_temp
    else:
        a2i = app2interp
    for name, obj in d.items():
        if name.startswith('app_') and name[4:] not in d:
            if isinstance(obj, types.FunctionType):
                d[name[4:]] = a2i(obj, name[4:])

def build_dict(d, space):
    """Search all Gateways and put them into a wrapped dictionary."""
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
    def getcache(self, space): 
        return self.__dict__.setdefault(space, {}) 
        #                               ^^^^^
        #                          armin suggested this 
     
class interp2app_temp(interp2app): 
    def getcache(self, space): 
        return self.__dict__.setdefault(space, {}) 
