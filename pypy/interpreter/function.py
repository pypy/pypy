"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable

class Function(Wrappable):
    """A function is a code object captured with some environment:
    an object space, a dictionary of globals, default arguments,
    and an arbitrary 'closure' passed to the code object."""
    
    def __init__(self, space, code, w_globals=None, defs_w=[], closure=None, forcename=None):
        self.space = space
        self.name = forcename or code.co_name
        self.w_doc = None   # lazily read and wrapped from code.co_consts[0]
        self.code = code       # Code instance
        self.w_func_globals = w_globals  # the globals dictionary
        self.closure   = closure    # normally, list of Cell instances or None
        self.defs_w    = defs_w     # list of w_default's
        self.w_func_dict = space.newdict([])

    def call_function(self, *args_w, **kwds_w):
        scope_w = self.parse_args(list(args_w), kwds_w)
        frame = self.code.create_frame(self.space, self.w_func_globals,
                                            self.closure)
        frame.setfastscope(scope_w)
        return frame.run()

    def parse_args(self, args_w, kwds_w):
        """ parse args and kwargs to initialize the frame.
        """
        space = self.space
        signature = self.code.signature()
        argnames, varargname, kwargname = signature
        #
        #   args_w = list of the normal actual parameters, wrapped
        #   kwds_w = real dictionary {'keyword': wrapped parameter}
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        # We try to give error messages following CPython's, which are
        # very informative.
        #
        co_argcount = len(argnames) # expected formal arguments, without */**

        # put as many positional input arguments into place as available
        scope_w = args_w[:co_argcount]
        input_argcount = len(scope_w)

        # check that no keyword argument conflicts with these
        if kwds_w:
            for name in argnames[:input_argcount]:
                if name in kwds_w:
                    self.raise_argerr_multiple_values(name)

        remainingkwds_w = kwds_w.copy()
        if input_argcount < co_argcount:
            # not enough args, fill in kwargs or defaults if exists
            def_first = co_argcount - len(self.defs_w)
            for i in range(input_argcount, co_argcount):
                name = argnames[i]
                if name in remainingkwds_w:
                    scope_w.append(remainingkwds_w[name])
                    del remainingkwds_w[name]
                elif i >= def_first:
                    scope_w.append(self.defs_w[i-def_first])
                else:
                    self.raise_argerr(args_w, kwds_w, False)
                    
        # collect extra positional arguments into the *vararg
        if varargname is not None:
            scope_w.append(space.newtuple(args_w[co_argcount:]))
        elif len(args_w) > co_argcount:
            self.raise_argerr(args_w, kwds_w, True)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            w_kwds = space.newdict([(space.wrap(key), w_value)
                                    for key, w_value in remainingkwds_w.items()])
            scope_w.append(w_kwds)
        elif remainingkwds_w:
            self.raise_argerr_unknown_kwds(remainingkwds_w)
        return scope_w

    # helper functions to build error message for the above

    def raise_argerr(self, args_w, kwds_w, too_many):
        argnames, varargname, kwargname = self.code.signature()
        nargs = len(args_w)
        n = len(argnames)
        if n == 0:
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
                nargs += len(kwds_w)
            msg = "%s() takes no %sargument (%d given)" % (
                self.name, 
                msg2,
                nargs)
        else:
            defcount = len(self.defs_w)
            if defcount == 0:
                msg1 = "exactly"
            elif too_many:
                msg1 = "at most"
            else:
                msg1 = "at least"
                n -= defcount
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
            if n == 1:
                plural = ""
            else:
                plural = "s"
            msg = "%s() takes %s %d %sargument%s (%d given)" % (
                self.name,
                msg1,
                n,
                msg2,
                plural,
                nargs)
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))

    def raise_argerr_multiple_values(self, argname):
        msg = "%s() got multiple values for keyword argument %s" % (
            self.name,
            argname)
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))

    def raise_argerr_unknown_kwds(self, kwds_w):
        if len(kwds_w) == 1:
            msg = "%s() got an unexpected keyword argument '%s'" % (
                self.name,
                kwds_w.keys()[0])
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                self.name,
                len(kwds_w))
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))

    def getdict(self):
        return self.w_func_dict

    def setdict(self, w_dict):
        self.w_func_dict = w_dict

    def descr_function_get(self, w_obj, w_cls=None):
        space = self.space
        wrap = space.wrap
        asking_for_bound = (w_cls == space.w_None or
                      not space.is_true(space.is_(w_obj, space.w_None)) or
                      space.is_true(space.is_(w_cls, space.type(space.w_None))))
        if asking_for_bound:
            if w_cls == space.w_None:
                w_cls = space.type(w_obj)
            return wrap(Method(space, wrap(self), w_obj, w_cls))
        else:
            return wrap(Method(space, wrap(self), None, w_cls))

    def descr_function_call(self, *args_w, **kwds_w):
        return self.call_function(*args_w, **kwds_w)

    def fget_func_defaults(space, w_self):
        self = space.unwrap(w_self)
        values_w = self.defs_w
        if not values_w:
            return space.w_None
        return space.newtuple(values_w)

    def fget_func_doc(space, w_self):
        self = space.unwrap(w_self)
        if self.w_doc is None:
            doc = getattr(self.code, 'co_consts', (None,))[0]
            self.w_doc = space.wrap(doc)
        return self.w_doc

    def fset_func_doc(space, w_self, w_doc):
        self = space.unwrap(w_self)
        self.w_doc = w_doc

    def fdel_func_doc(space, w_self):
        self = space.unwrap(w_self)
        self.w_doc = space.w_None

class Method(Wrappable): 
    """A method is a function bound to a specific instance or class."""

    def __init__(self, space, w_function, w_instance, w_class):
        self.space = space
        self.w_function = w_function
        self.w_instance = w_instance   # or None
        self.w_class = w_class

    def call_function(self, *args_w, **kwds_w):
        if self.w_instance is not None:
            # bound method
            return self.space.call_function(self.w_function, self.w_instance,
                                            *args_w, **kwds_w)
        else:
            # unbound method
            if (len(args_w) >= 1 and self.space.is_true(
                    self.space.isinstance(args_w[0], self.w_class))):
                pass  # ok
            else:
                msg = ("unbound method must be called with "
                       "instance as first argument")     # XXX fix error msg
                raise OperationError(self.space.w_TypeError,
                                     self.space.wrap(msg))
            return self.space.call_function(self.w_function, *args_w, **kwds_w)

    def descr_method_call(self, *args_w, **kwds_w):
        return self.call_function(*args_w, **kwds_w)

class StaticMethod(Wrappable):
    """A static method.  Note that there is one class staticmethod at
    app-level too currently; this is only used for __new__ methods."""

    def __init__(self, w_function):
        self.w_function = w_function

    def descr_staticmethod_get(self, w_obj, w_cls=None):
        return self.w_function
