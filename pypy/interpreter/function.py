"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments

class Function(Wrappable):
    """A function is a code object captured with some environment:
    an object space, a dictionary of globals, default arguments,
    and an arbitrary 'closure' passed to the code object."""
    
    def __init__(self, space, code, w_globals=None, defs_w=[], closure=None, forcename=None):
        self.space = space
        self.name = forcename or code.co_name
        self.w_doc = None   # lazily read and wrapped from code.getdocstring()
        self.code = code       # Code instance
        self.w_func_globals = w_globals  # the globals dictionary
        self.closure   = closure    # normally, list of Cell instances or None
        self.defs_w    = defs_w     # list of w_default's
        self.w_func_dict = space.newdict([])

    def __repr__(self):
        # return "function %s.%s" % (self.space, self.name)
        # maybe we want this shorter:
        return "<Function %s>" % self.name

    def call_args(self, args):
        scope_w = args.parse(self.name, self.code.signature(), self.defs_w)
        frame = self.code.create_frame(self.space, self.w_func_globals,
                                            self.closure)
        frame.setfastscope(scope_w)
        return frame.run()

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

    def descr_function_call(self, __args__):
        return self.call_args(__args__)

    def fget_func_defaults(space, w_self):
        self = space.unwrap(w_self)
        values_w = self.defs_w
        if not values_w:
            return space.w_None
        return space.newtuple(values_w)

    def fget_func_doc(space, w_self):
        self = space.unwrap(w_self)
        if self.w_doc is None:
            self.w_doc = space.wrap(self.code.getdocstring())
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
        
    def __repr__(self):
        if self.w_instance:
            pre = "bound"
        else:
            pre = "unbound"
        return "%s method %s" % (pre, self.w_function.name)

    def call_args(self, args):
        if self.w_instance is not None:
            # bound method
            args = args.prepend(self.w_instance)
        else:
            # unbound method
            w_firstarg = args.firstarg()
            if w_firstarg is not None and self.space.is_true(
                    self.space.isinstance(w_firstarg, self.w_class)):
                pass  # ok
            else:
                msg = ("unbound method must be called with "
                       "instance as first argument")     # XXX fix error msg
                raise OperationError(self.space.w_TypeError,
                                     self.space.wrap(msg))
        return self.space.call_args(self.w_function, args)

    def descr_method_get(self, w_obj, w_cls=None):
        space = self.space
        if self.w_instance is not None:
            return space.wrap(self)    # already bound
        else:
            # only allow binding to a more specific class than before
            if w_cls == space.w_None:
                w_cls = space.type(w_obj)
            if not space.is_true(space.issubtype(w_cls, self.w_class)):
                return space.wrap(self)   # subclass test failed
            return space.get(self.w_function, w_obj, w_cls)

    def descr_method_call(self, __args__):
        return self.call_args(__args__)

    def descr_method_getattribute(self, w_attr):
        space = self.space
        w_self = space.wrap(self)
        w_result = space.lookup(w_self, space.unwrap(w_attr))
        if w_result is None:
            return space.getattr(self.w_function, w_attr)
        else:
            return space.get(w_result, w_self)

class StaticMethod(Wrappable):
    """A static method.  Note that there is one class staticmethod at
    app-level too currently; this is only used for __new__ methods."""

    def __init__(self, w_function):
        self.w_function = w_function

    def descr_staticmethod_get(self, w_obj, w_cls=None):
        return self.w_function
