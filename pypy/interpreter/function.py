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
        self.doc = getattr(code, 'co_consts', (None,))[0]
        self.code = code       # Code instance
        self.w_func_globals = w_globals  # the globals dictionary
        self.closure   = closure    # normally, list of Cell instances or None
        self.defs_w    = defs_w     # list of w_default's
        self.w_func_dict = space.newdict([])

    def call(self, w_args, w_kwds=None):
        scope_w = self.parse_args(w_args, w_kwds)
        frame = self.code.create_frame(self.space, self.w_func_globals,
                                            self.closure)
        frame.setfastscope(scope_w)
        return frame.run()

    def parse_args(self, w_args, w_kwds=None):
        """ parse args and kwargs to initialize the frame.
        """
        space = self.space
        signature = self.code.signature()
        argnames, varargname, kwargname = signature
        #
        #   w_args = wrapped sequence of the normal actual parameters
        #   args_w = the same, as a list of wrapped actual parameters
        #   w_kwds = wrapped dictionary of keyword parameters or a real None
        #   argnames = list of formal parameter names
        #   scope_w = resulting list of wrapped values
        #
        # We try to give error messages following CPython's, which are
        # very informative.
        #
        if w_kwds is None or not space.is_true(w_kwds):
            w_kwargs = space.newdict([])
        else:
            # space.is_true() above avoids infinite recursion copy<->parse_args
            w_kwargs = space.call_method(w_kwds, "copy")

        co_argcount = len(argnames) # expected formal arguments, without */**

        # put as many positional input arguments into place as available
        args_w = space.unpacktuple(w_args)
        scope_w = args_w[:co_argcount]
        input_argcount = len(scope_w)

        # check that no keyword argument conflicts with these
        for name in argnames[:input_argcount]:
            w_name = space.wrap(name)
            if space.is_true(space.contains(w_kwargs, w_name)):
                self.raise_argerr_multiple_values(name)

        if input_argcount < co_argcount:
            # not enough args, fill in kwargs or defaults if exists
            def_first = co_argcount - len(self.defs_w)
            for i in range(input_argcount, co_argcount):
                w_name = space.wrap(argnames[i])
                if space.is_true(space.contains(w_kwargs, w_name)):
                    scope_w.append(space.getitem(w_kwargs, w_name))
                    space.delitem(w_kwargs, w_name)
                elif i >= def_first:
                    scope_w.append(self.defs_w[i-def_first])
                else:
                    self.raise_argerr(w_args, w_kwds, False)
                    
        # collect extra positional arguments into the *vararg
        if varargname is not None:
            scope_w.append(space.newtuple(args_w[co_argcount:]))
        elif len(args_w) > co_argcount:
            self.raise_argerr(w_args, w_kwds, True)

        # collect extra keyword arguments into the **kwarg
        if kwargname is not None:
            # XXX this doesn't check that the keys of kwargs are strings
            scope_w.append(w_kwargs)
        elif space.is_true(w_kwargs):
            self.raise_argerr_unknown_kwds(w_kwds)
        return scope_w

    # helper functions to build error message for the above

    def raise_argerr(self, w_args, w_kwds, too_many):
        argnames, varargname, kwargname = self.code.signature()
        nargs = self.space.unwrap(self.space.len(w_args))
        n = len(argnames)
        if n == 0:
            if kwargname is not None:
                msg2 = "non-keyword "
            else:
                msg2 = ""
                nargs += self.space.unwrap(self.space.len(w_kwds))
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

    def raise_argerr_unknown_kwds(self, w_kwds):
        nkwds = self.space.unwrap(self.space.len(w_kwds))
        if nkwds == 1:
            w_iter = self.space.iter(w_kwds)
            w_key = self.space.next(w_iter)
            msg = "%s() got an unexpected keyword argument '%s'" % (
                self.name,
                self.space.unwrap(w_key))
        else:
            msg = "%s() got %d unexpected keyword arguments" % (
                self.name,
                nkwds)
        raise OperationError(self.space.w_TypeError, self.space.wrap(msg))
   
    def descr_function_get(self, w_obj, w_cls):
        space = self.space
        wrap = space.wrap
        if not space.is_true(space.is_(w_obj, space.w_None)):
            if space.is_true(space.is_(w_cls, space.w_None)):
                w_cls = space.type(w_obj)
            return wrap(Method(space, wrap(self), w_obj, w_cls))
        else:
            return wrap(Method(space, wrap(self), None, w_cls))


class Method(object):
    """A method is a function bound to a specific instance or class."""

    def __init__(self, space, w_function, w_instance, w_class):
        self.space = space
        self.w_function = w_function
        self.w_instance = w_instance   # or None
        self.w_class = w_class

    def call(self, w_args, w_kwds=None):
        args_w = self.space.unpacktuple(w_args)
        if self.w_instance is not None:
            # bound method
            args_w = [self.w_instance] + args_w
            w_args = self.space.newtuple(args_w)
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
        return self.space.call(self.w_function, w_args, w_kwds)
