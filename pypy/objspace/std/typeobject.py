from pypy.interpreter import pycode
from pypy.objspace.std.objspace import *
from pypy.objspace.std.dictobject import W_DictObject


class W_TypeObject(W_Object):
    delegate_once = {}
    statictypename = 'type'

    def __init__(w_self, space, w_tpname):
        W_Object.__init__(w_self, space)
        w_self.w_tpname = w_tpname
        w_self.builtin_implementations = []
        w_self.multimethods = {}
        # HACK to get to the multimethods of the space
        for key, value in space.__class__.__dict__.iteritems():
            if isinstance(value, MultiMethod):
                for i in range(len(value.specialnames)):
                    w_self.multimethods[value.specialnames[i]] = value, i

    def setup_builtin_type(w_self, implementation):
        implementation.statictype = w_self
        w_self.builtin_implementations.append(implementation)
        
        for key, value in implementation.__dict__.iteritems():
            if isinstance(value, implmethod):
                try:
                    multimethod, bound_pos = w_self.multimethods[key]
                except KeyError:
                    sample = value.dispatch_table.keys()[0]
                    multimethod = MultiMethod('%s()' % key, len(sample)+1, [])
                    w_self.multimethods[key] = multimethod, None
                for types, func in value.dispatch_table.iteritems():
                    multimethod.register(func, implementation, *types)

    def lookup(w_self, space, w_key):
        "XXX at some point, turn this into a multimethod"
        key = space.unwrap(w_key)
        assert isinstance(key, str)
        try:
            multimethod, bound_pos = w_self.multimethods[key]
        except KeyError:
            raise KeyError
        multimethod = multimethod.__get__(space, None)
        code = PyMultimethodCode(multimethod, bound_pos, w_self)
        if code.multimethod.is_empty():
            raise KeyError
        return space.newfunction(code, space.w_None, space.w_None)


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
            # 'bound_pos' hack mode on
            multimethod = multimethod.slicetable(bound_position or 0, w_type)
            # 'bound_pos' hack mode off
            if bound_position:
                argnames.insert(0, argnames.pop(bound_position))
        # 'bound_pos' hack mode on
        self.prepend_space_argument = bound_position is not None
        # 'bound_pos' hack mode off
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
            return multimethod.perform_call(dispatchargs, initialtypes,
                prepend_space_argument = self.prepend_space_argument)
        except FailedToImplement, e:
            if e.args:
                raise OperationError(*e.args)
            else:
                return space.w_NotImplemented
