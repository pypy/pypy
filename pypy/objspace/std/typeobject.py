from pypy.interpreter import pycode
from pypy.objspace.std.objspace import *


class W_TypeObject(W_Object):
    delegate_once = {}
    statictypename = 'type'

    def __init__(w_self, space, w_tpname):
        W_Object.__init__(w_self, space)
        w_self.w_tpname = w_tpname
        w_self.builtin_implementations = []
        w_self.multimethods = [value for key, value in space.__dict__.iteritems()
                                     if isinstance(value, MultiMethod)]

    def setup_builtin_type(w_self, implementation):
        implementation.statictype = w_self
        w_self.builtin_implementations.append(implementation)


def make_type_by_name(space, tpname):
    try:
        w_type = space.TYPE_CACHE[tpname]
    except KeyError:
        w_type = space.TYPE_CACHE[tpname] = W_TypeObject(space,
                                                         space.wrap(tpname))
    return w_type


class PyMultimethodCode(pycode.PyBaseCode):
    
    def __init__(self, multimethod, bound_position=None, w_type=None):
        pycode.PyBaseCode.__init__(self)
        argnames = ['x%d'%(i+1) for i in range(multimethod.multimethod.arity)]
        if w_type is not None:
            multimethod = multimethod.slicetable(bound_position, w_type)
            argnames.insert(0, argnames.pop(bound_position))
        self.multimethod = multimethod
        self.co_name = multimethod.multimethod.operatorsymbol
        self.co_flags = 0
        self.co_varnames = tuple(argnames)
        self.co_argcount = multimethod.multimethod.arity

    def eval_code(self, space, w_globals, w_locals):
        """Call the multimethod, ignoring all implementations that do not
        have exactly the expected type at the bound_position."""
        multimethod = self.multimethod
        dispatchargs = []
        initialtypes = []
        for i in range(multimethod.multimethod.arity):
            w_arg = space.getitem(w_locals, space.wrap('x%d'%(i+1)))
            dispatchargs.append(w_arg)
            initialtypes.append(w_arg.get_builtin_impl_class())
        dispatchargs = tuple(dispatchargs)
        initialtypes = tuple(initialtypes)
        try:
            return multimethod.perform_call(dispatchargs, initialtypes)
        except FailedToImplement, e:
            if e.args:
                raise OperationError(*e.args)
            else:
                return space.w_NotImplemented
