from pypy.interpreter import pycode
from pypy.objspace.std.objspace import *


class W_TypeObject(W_Object):
    delegate_once = {}
    #statictype = W_TypeType    (hacked into place in typetype.py)

    def __init__(w_self, space):
        W_Object.__init__(w_self, space)
        w_self.w_tpname = space.wrap(w_self.typename)
        w_self.multimethods = {}
        # import all multimethods of the space and of the type class
        for multimethod in (hack_out_multimethods(space) +
                            hack_out_multimethods(w_self)):
            for i in range(len(multimethod.specialnames)):
                w_self.multimethods[multimethod.specialnames[i]] = multimethod, i

##    XXX remove me
##    def setup_builtin_type(w_self, implementation):
##        implementation.statictype = w_self
##        w_self.builtin_implementations.append(implementation)
##        
##        for key, value in implementation.__dict__.iteritems():
##            if isinstance(value, implmethod):
##                try:
##                    multimethod, bound_pos = w_self.multimethods[key]
##                except KeyError:
##                    sample = value.dispatch_table.keys()[0]
##                    multimethod = MultiMethod('%s()' % key, len(sample)+1, [])
##                    w_self.multimethods[key] = multimethod, None
##                for types, func in value.dispatch_table.iteritems():
##                    multimethod.register(func, implementation, *types)

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


def hack_out_multimethods(instance):
    return [value for value in instance.__class__.__dict__.itervalues()
                  if isinstance(value, MultiMethod)]


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


def type_call(space, w_type, w_args, w_kwds):
    w_newobject = space.new(w_type, w_args, w_kwds)
    # XXX call __init__() later
    return w_newobject
    
##    #        H  H   AA    CCC  K  K
##    #        H  H  A  A  C     K K
##    #        HHHH  A  A  C     KK
##    #        H  H  AAAA  C     K K
##    #        H  H  A  A   CCC  K  K

##    tpname = space.unwrap(w_type.w_tpname)
##    args = space.unpackiterable(w_args)
##    if tpname == 'type':
##        assert len(args) == 1
##        return space.type(args[0])
##    if tpname == 'list':
##        assert len(args) == 1
##        return space.newlist(space.unpackiterable(args[0]))
##    if tpname == 'tuple':
##        assert len(args) == 1
##        return space.newtuple(space.unpackiterable(args[0]))
##    if tpname == 'str':
##        assert len(args) == 1
##        return space.str(args[0])

##    import __builtin__
##    hacky = getattr(__builtin__, tpname)(
##        *space.unwrap(w_args), **space.unwrap(w_kwds))
##    return space.wrap(hacky)

StdObjSpace.call.register(type_call, W_TypeObject, W_ANY, W_ANY)
