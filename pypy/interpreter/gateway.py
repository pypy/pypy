"""

Gateway between app-level and interpreter-level:
* BuiltinCode (call interp-level code from app-level)
* Gateway     (a space-independent gateway to a Code object)
* app2interp  (embed an app-level function into an interp-level callable)
* interp2app  (publish an interp-level object to be visible from app-level)
* exportall   (mass-call interp2app on a whole dict of objects)
* importall   (mass-call app2interp on a whole dict of objects)

"""

import types
from weakref import WeakKeyDictionary
from pypy.interpreter import eval, pycode
from pypy.interpreter.baseobjspace import Wrappable, ObjSpace
from pypy.interpreter.function import Function, Method


class BuiltinCode(eval.Code):
    "The code object implementing a built-in (interpreter-level) hook."

    # When a BuiltinCode is stored in a Function object,
    # you get the functionality of CPython's built-in function type.

    def __init__(self, func):
        # 'implfunc' is the interpreter-level function.
        # Note that this uses a lot of (construction-time) introspection.
        eval.Code.__init__(self, func.__name__)
        self.func = func
        # extract the signature from the (CPython-level) code object
        tmp = pycode.PyCode(None)
        tmp._from_code(func.func_code)
        self.sig = tmp.signature()
        self.ismethod = False

    def create_frame(self, space, w_globals, closure=None):
        return BuiltinFrame(space, self, w_globals)

    def signature(self):
        return self.sig


class BuiltinFrame(eval.Frame):
    "Frame emulation for BuiltinCode."
    # This is essentially just a delegation to the 'func' of the BuiltinCode.
    # Initialization of locals is already done by the time run() is called,
    # via the interface defined in eval.Frame.

    def run(self):
        argarray = self.fastlocals_w
        if self.code.ismethod:
            argarray = [self.space.unwrap(argarray[0])] + argarray[1:]
        else:
            argarray = [self.space] + argarray
        return call_with_prepared_arguments(self.space, self.code.func,
                                            argarray)


def call_with_prepared_arguments(space, function, argarray):
    """Call the given function. 'argarray' is a correctly pre-formatted
    list of values for the formal parameters, including one for * and one
    for **."""
    # XXX there is no clean way to do this in Python,
    # we have to hack back an arguments tuple and keywords dict.
    # This algorithm is put in its own well-isolated function so that
    # you don't need to look at it :-)
    keywords = {}
    co = function.func_code
    if co.co_flags & 8:  # CO_VARKEYWORDS
        w_kwds = argarray[-1]
        for w_key in space.unpackiterable(w_kwds):
            keywords[space.unwrap(w_key)] = space.getitem(w_kwds, w_key)
        argarray = argarray[:-1]
    if co.co_flags & 4:  # CO_VARARGS
        w_varargs = argarray[-1]
        argarray = argarray[:-1] + space.unpacktuple(w_varargs)
    return function(*argarray, **keywords)


class Gateway(object):
    """General-purpose utility for the interpreter-level to create callables
    that transparently invoke code objects (and thus possibly interpreted
    app-level code)."""

    # This is similar to a Function object, but not bound to a particular
    # object space. During the call, the object space is either given
    # explicitely as the first argument (for plain function), or is read
    # from 'self.space' for methods.

    def __init__(self, name, code, staticglobals=None, staticdefs=[]):
        self.name = name
        self.code = code
        self.staticglobals = staticglobals
        self.staticdefs = staticdefs
        self.functioncache = WeakKeyDictionary()  # map {space: Function}

    def __wrap__(self, space):
        # to wrap a Gateway, we first make a real Function object out of it
        # and the result is a wrapped version of this Function.
        return space.wrap(self.get_function(space))

    def __call__(self, space, *args_w, **kwds_w):
        # to call the Gateway as a non-method, 'space' must be explicitely
        # supplied. We build the Function object and call it.
        fn = self.get_function(space)
        return fn(*args_w, **kwds_w)

    def __get__(self, obj, cls=None):
        # to get the Gateway as a method out of an instance, we build a
        # Function and get it.
        if obj is None:
            return self   # Gateways as unbound methods not implemented
        else:
            # the object space is implicitely fetched out of the instance
            fn = self.get_function(obj.space)
            self.code.ismethod = True   # that's a hack all right
            return fn.__get__(obj, cls)

    def get_function(self, space):
        try:
            return self.functioncache[space]
        except KeyError:
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
                for value in self.staticglobals.itervalues():
                    if isinstance(value, Gateway):
                        if space in value.functioncache:
                            # yes, we share its w_globals
                            fn = value.functioncache[space]
                            w_globals = fn.w_globals
                            break
                else:
                    # no, we build all Gateways in the staticglobals now.
                    w_globals = build_dict(self.staticglobals, space)
            return self.build_function(space, w_globals)

    def build_function(self, space, w_globals):
        if space in self.functioncache:
            fn = self.functioncache[space]
        else:
            defs_w = [space.wrap(def_value) for def_value in self.staticdefs]
            fn = Function(space, self.code, w_globals, defs_w)
            self.functioncache[space] = fn
        return fn


def app2interp(app, app_name=None):
    """Build a Gateway that calls 'app' at app-level."""
    # app must be a function whose name starts with 'app_'.
    if not isinstance(app, types.FunctionType):
        if isinstance(app, Gateway):
            return app
        raise TypeError, "function expected, got %r instead" % app
    if app_name is None:
        if not app.func_name.startswith('app_'):
            raise ValueError, ("function name must start with 'app_'; "
                               "%r does not" % app.func_name)
        app_name = app.func_name[4:]
    code = pycode.PyCode(None)
    code._from_code(app.func_code)
    staticglobals = app.func_globals
    staticdefs = list(app.func_defaults or ())
    return Gateway(app_name, code, staticglobals, staticdefs)

def interp2app(f, app_name=None):
    """Build a Gateway that calls 'f' at interp-level."""
    # f must be a function whose name does NOT starts with 'app_'
    if not isinstance(f, types.FunctionType):
        if isinstance(f, Gateway):
            return f
        raise TypeError, "function expected, got %r instead" % f
    if app_name is None:
        if f.func_name.startswith('app_'):
            raise ValueError, ("function name %r suspiciously starts "
                               "with 'app_'" % f.func_name)
        app_name = f.func_name
    builtincode = BuiltinCode(f)
    staticdefs = list(f.func_defaults or ())
    return Gateway(app_name, builtincode, None, staticdefs)


def exportall(d):
    """Publish every function from a dict."""
    for name, obj in d.items():
        # ignore names in '_xyz'
        if not name.startswith('_') or name.endswith('_'):
            if isinstance(obj, types.FunctionType):
                if 'app_'+name not in d:
                    d['app_'+name] = interp2app(obj, name)

def importall(d):
    """Import all app_-level functions as Gateways into a dict."""
    for name, obj in d.items():
        if name.startswith('app_') and name[4:] not in d:
            if isinstance(obj, types.FunctionType):
                d[name[4:]] = app2interp(obj, name[4:])

def build_dict(d, space):
    """Search all Gateways and put them into a wrapped dictionary."""
    w_globals = space.newdict([])
    for value in d.itervalues():
        if isinstance(value, Gateway):
            fn = value.build_function(space, w_globals)
            w_name = space.wrap(value.name)
            w_object = space.wrap(fn)
            space.setitem(w_globals, w_name, w_object)
    return w_globals
