"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.eval import Code

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
        self.w_module = None

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
        space = self.space
        if not space.is_true(space.isinstance( w_dict, space.w_dict )):
            raise OperationError( space.w_TypeError, space.wrap("setting function's dictionary to a non-dict") )
        self.w_func_dict = w_dict

    def descr_function_get(self, w_obj, w_cls=None):
        space = self.space
        wrap = space.wrap
        asking_for_bound = (w_cls == space.w_None or
                      not space.is_true(space.is_(w_obj, space.w_None)) or
                      space.is_true(space.is_(w_cls, space.type(space.w_None))))
        if asking_for_bound:
            #if w_cls == space.w_None:
            #    w_cls = space.type(w_obj)
            return wrap(Method(space, wrap(self), w_obj, w_cls))
        else:
            return wrap(Method(space, wrap(self), None, w_cls))

    def descr_function_call(self, __args__):
        return self.call_args(__args__)

    def fget_func_defaults(space, w_self):
        self = space.interpclass_w(w_self)
        values_w = self.defs_w
        if not values_w:
            return space.w_None
        return space.newtuple(values_w)
    
    def fset_func_defaults(space, w_self, w_defaults):
        self = space.interpclass_w(w_self)
        if not space.is_true( space.isinstance( w_defaults, space.w_tuple ) ):
            raise OperationError( space.w_TypeError, space.wrap("func_defaults must be set to a tuple object") )
        self.defs_w = space.unpackiterable( w_defaults )

    def fdel_func_defaults(space, w_self):
        self = space.interpclass_w(w_self)
        self.defs_w = []

    def fget_func_doc(space, w_self):
        self = space.interpclass_w(w_self)
        if self.w_doc is None:
            self.w_doc = space.wrap(self.code.getdocstring())
        return self.w_doc

    def fset_func_doc(space, w_self, w_doc):
        self = space.interpclass_w(w_self)
        self.w_doc = w_doc

    def fdel_func_doc(space, w_self):
        self = space.interpclass_w(w_self)
        self.w_doc = space.w_None

    def fget___module__(space, w_self):
        self = space.interpclass_w(w_self)
        if self.w_module is None:
            if self.w_func_globals is not None and not space.is_w(self.w_func_globals, space.w_None):
                self.w_module = space.call_method( self.w_func_globals, "get", space.wrap("__name__") )
            else:
                self.w_module = space.w_None
        return self.w_module
        
    def fset___module__(space, w_self, w_module):
        self = space.interpclass_w(w_self)
        self.w_module = w_module
    
    def fdel___module__(space, w_self):
        self = space.interpclass_w(w_self)
        self.w_module = space.w_None

    def fget_func_code(space, w_self):
        self = space.interpclass_w(w_self)
        return space.wrap(self.code)

    def fset_func_code(space, w_self, w_code):
        self = space.interpclass_w(w_self)
        code = space.interpclass_w(w_code)
        if not isinstance(code, Code ):
            raise OperationError( space.w_TypeError, space.wrap("func_code must be set to a code object") )
        self.code = code
    
    def fget_func_closure(space, w_self):
        self = space.interpclass_w(w_self)
        if self.closure is not None:
            w_res = space.newtuple( [ space.wrap(i) for i in self.closure ] )
        else:
            w_res = space.w_None
        return w_res


class Method(Wrappable): 
    """A method is a function bound to a specific instance or class."""

    def __init__(self, space, w_function, w_instance, w_class):
        self.space = space
        self.w_function = w_function
        self.w_instance = w_instance   # or None
        self.w_class = w_class
        
    def descr_method__new__(space, w_subtype, w_function, w_instance, w_class):
        method = space.allocate_instance(Method, w_subtype)
        if space.is_w( w_instance, space.w_None ):
            w_instance = None
        method.__init__(space, w_function, w_instance, w_class)
        return space.wrap(method)

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
                    self.space.abstract_isinstance(w_firstarg, self.w_class)):
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
            #if w_cls == space.w_None:
            #    w_cls = space.type(w_obj)
            if w_cls is not None and w_cls != space.w_None and not space.is_true(space.abstract_issubclass(w_cls, self.w_class)):
                return space.wrap(self)   # subclass test failed
            return space.get(self.w_function, w_obj, w_cls)

    def descr_method_call(self, __args__):
        return self.call_args(__args__)

    def descr_method_getattribute(self, w_attr):
        space = self.space
        w_self = space.wrap(self)
        w_result = space.lookup(w_self, space.str_w(w_attr))
        if w_result is None:
            return space.getattr(self.w_function, w_attr)
        else:
            return space.get(w_result, w_self)

    def descr_method_eq(self, w_other):
        space = self.space
        other = space.interpclass_w(w_other)
        if not isinstance(other, Method):
            return space.w_False
        if not space.is_w(self.w_instance, other.w_instance):
            return space.w_False
        return space.eq(self.w_function, other.w_function)

class StaticMethod(Wrappable):
    """A static method.  Note that there is one class staticmethod at
    app-level too currently; this is only used for __new__ methods."""

    def __init__(self, w_function):
        self.w_function = w_function

    def descr_staticmethod_get(self, w_obj, w_cls=None):
        return self.w_function
