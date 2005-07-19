"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.eval import Code
from pypy.interpreter.gateway import NoneNotWrapped

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

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance( w_dict, space.w_dict )):
            raise OperationError( space.w_TypeError, space.wrap("setting function's dictionary to a non-dict") )
        self.w_func_dict = w_dict

    # unwrapping is done through unwrap_specs in typedef.py

    def descr_method__new__(space, w_subtype, w_code, w_globals, 
                            w_name=None, w_argdefs=None, w_closure=NoneNotWrapped):
        code = space.interpclass_w(w_code)
        if code is None or not isinstance(code, Code):
            raise OperationError(space.w_TypeError, space.wrap("expected code"))
        if not space.is_true(space.isinstance(w_globals, space.w_dict)):
            raise OperationError(space.w_TypeError, space.wrap("expected dict"))
        if not space.is_w(w_name, space.w_None):
            name = space.str_w(w_name)
        else:
            name = None
        if not space.is_w(w_argdefs, space.w_None):
            defs_w = space.unpackiterable(w_argdefs)
        else:
            defs_w = []
        if w_closure is None:
            closure = None
        elif not space.is_w(space.type(w_closure), space.w_tuple):
            raise OperationError(space.w_TypeError, space.wrap("invalid closure"))
        else:
            from pypy.interpreter.pycode import PyCode
            from pypy.interpreter.nestedscope import Cell
            closure_w = space.unpackiterable(w_closure)
            n = len(closure_w)
            if not isinstance(code, PyCode) or len(code.co_freevars) == 0:
                raise OperationError(space.w_ValueError, space.wrap("no closure needed"))
            elif len(code.co_freevars) != n:
                raise OperationError(space.w_ValueError, space.wrap("closure is wrong size"))
            closure = []
            for w_cell in closure_w:
                cell = space.interpclass_w(w_cell)
                if not isinstance(cell, Cell):
                    raise OperationError(space.w_TypeError, space.wrap("non-cell in closure"))
                closure.append(cell)
        func = space.allocate_instance(Function, w_subtype)
        Function.__init__(func, space, code, w_globals, defs_w, closure, name)
        return space.wrap(func)

    def descr_function_call(self, __args__):
        return self.call_args(__args__)

    def descr_function_repr(self):
        return self.getrepr(self.space, 'function %s' % (self.name,))

    def fget_func_defaults(space, self):
        values_w = self.defs_w
        if not values_w:
            return space.w_None
        return space.newtuple(values_w)

    def fset_func_defaults(space, self, w_defaults):
        if not space.is_true( space.isinstance( w_defaults, space.w_tuple ) ):
            raise OperationError( space.w_TypeError, space.wrap("func_defaults must be set to a tuple object") )
        self.defs_w = space.unpackiterable( w_defaults )

    def fdel_func_defaults(space, self):
        self.defs_w = []

    def fget_func_doc(space, self):
        if self.w_doc is None:
            self.w_doc = space.wrap(self.code.getdocstring())
        return self.w_doc

    def fset_func_doc(space, self, w_doc):
        self.w_doc = w_doc

    def fget_func_name(space, self):
        return space.wrap(self.name)

    def fset_func_name(space, self, w_name):
        try:
            self.name = space.str_w(w_name)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                raise OperationError(space.w_TypeError,
                                     space.wrap("func_name must be set "
                                                "to a string object"))
            raise


    def fdel_func_doc(space, self):
        self.w_doc = space.w_None

    def fget___module__(space, self):
        if self.w_module is None:
            if self.w_func_globals is not None and not space.is_w(self.w_func_globals, space.w_None):
                self.w_module = space.call_method( self.w_func_globals, "get", space.wrap("__name__") )
            else:
                self.w_module = space.w_None
        return self.w_module

    def fset___module__(space, self, w_module):
        self.w_module = w_module

    def fdel___module__(space, self):
        self.w_module = space.w_None

    def fget_func_code(space, self):
        return space.wrap(self.code)

    def fset_func_code(space, self, w_code):
        code = space.interpclass_w(w_code)
        if not isinstance(code, Code):
            raise OperationError(space.w_TypeError, space.wrap("func_code must be set to a code object") )
        if len(self.code.co_freevars) != len(code.co_freevars):
            raise OperationError(space.w_ValueError, space.wrap("%s() requires a code object with %s free vars, not %s " % (self.name, len(self.code.co_freevars), len(code.co_freevars))))
        self.code = code

    def fget_func_closure(space, self):
        if self.closure is not None:
            w_res = space.newtuple( [ space.wrap(i) for i in self.closure ] )
        else:
            w_res = space.w_None
        return w_res

def descr_function_get(space, w_function, w_obj, w_cls=None):
    """functionobject.__get__(obj[, type]) -> method"""
    # this is not defined as a method on Function because it's generally
    # useful logic: w_function can be any callable.  It is used by Method too.
    asking_for_bound = (space.is_w(w_cls, space.w_None) or
                        not space.is_w(w_obj, space.w_None) or
                        space.is_w(w_cls, space.type(space.w_None)))
    if asking_for_bound:
        #if w_cls == space.w_None:
        #    w_cls = space.type(w_obj)
        return space.wrap(Method(space, w_function, w_obj, w_cls))
    else:
        return space.wrap(Method(space, w_function, None, w_cls))


def _getclass(space, w_obj):
    try:
        return space.abstract_getclass(w_obj)
    except OperationError, e:
        if e.match(space, space.w_AttributeError):
            return space.type(w_obj)
        raise

class Method(Wrappable):
    """A method is a function bound to a specific instance or class."""

    def __init__(self, space, w_function, w_instance, w_class):
        self.space = space
        self.w_function = w_function
        self.w_instance = w_instance   # or None
        self.w_class = w_class         # possibly space.w_None

    def descr_method__new__(space, w_subtype, w_function, w_instance, w_class=None):
        if space.is_w( w_instance, space.w_None ):
            w_instance = None
        method = space.allocate_instance(Method, w_subtype)
        Method.__init__(method, space, w_function, w_instance, w_class)
        return space.wrap(method)

    def __repr__(self):
        if self.w_instance:
            pre = "bound"
        else:
            pre = "unbound"
        return "%s method %s" % (pre, self.w_function.getname(self.space, '?'))

    def call_args(self, args):
        space = self.space
        if self.w_instance is not None:
            # bound method
            args = args.prepend(self.w_instance)
        else:
            # unbound method
            w_firstarg = args.firstarg()
            if w_firstarg is not None and space.is_true(
                    space.abstract_isinstance(w_firstarg, self.w_class)):
                pass  # ok
            else:
                myname = self.getname(space,"")
                clsdescr = self.w_class.getname(space,"")
                if clsdescr:
                    clsdescr+=" "
                if w_firstarg is None:
                    instdescr = "nothing"
                else:
                    instname = _getclass(space, w_firstarg).getname(space,"")
                    if instname:
                        instname += " "
                    instdescr = "%sinstance" %instname
                msg = ("unbound method %s() must be called with %s"
                       "instance as first argument (got %s instead)")  % (myname, clsdescr, instdescr)
                raise OperationError(space.w_TypeError,
                                     space.wrap(msg))
        return space.call_args(self.w_function, args)

    def descr_method_get(self, w_obj, w_cls=None):
        space = self.space
        if self.w_instance is not None:
            return space.wrap(self)    # already bound
        else:
            # only allow binding to a more specific class than before
            #if w_cls == space.w_None:
            #    w_cls = space.type(w_obj)
            if (w_cls is not None and
                not space.is_w(w_cls, space.w_None) and
                not space.is_true(space.abstract_issubclass(w_cls, self.w_class))):
                return space.wrap(self)    # subclass test failed
            else:
                return descr_function_get(space, self.w_function, w_obj, w_cls)

    def descr_method_call(self, __args__):
        return self.call_args(__args__)

    def descr_method_repr(self):
        space = self.space
        name = self.w_function.getname(self.space, '?')
        # XXX do we handle all cases sanely here?
        if space.is_w(self.w_class, space.w_None):
            w_class = space.type(self.w_instance)
        else:
            w_class = self.w_class
        typename = w_class.getname(self.space, '?')
        if self.w_instance is None:
            s = "<method '%s' of '%s' objects>" %(name, typename)
            return space.wrap(s)
        else:
            info = "method %s of %s object" % (name, typename)
            return self.w_instance.getrepr(self.space, info)

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
        """staticmethod(x).__get__(obj[, type]) -> x"""
        return self.w_function

class BuiltinFunction(Function):

    def __init__(self, func):
        assert isinstance(func, Function)
        Function.__init__(self, func.space, func.code, func.w_func_globals,
                          func.defs_w, func.closure, func.name)
        self.w_doc = func.w_doc
        self.w_func_dict = func.w_func_dict
        self.w_module = func.w_module

    def descr_method__new__(space, w_subtype, w_func):
        func = space.interpclass_w(w_func)
        if func is None or not isinstance(func, Function):
            raise OperationError(space.w_TypeError,
                                 space.wrap("expected a function object"))
        bltin = space.allocate_instance(BuiltinFunction, w_subtype)
        BuiltinFunction.__init__(bltin, func)
        return space.wrap(bltin)

    def descr_function_repr(self):
        return self.space.wrap('<built-in function %s>' % (self.name,))
