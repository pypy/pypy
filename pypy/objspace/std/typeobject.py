from pypy.interpreter import pycode
from pypy.objspace.std.objspace import *


class W_TypeObject(W_Object):
    """This class is abstract.  Subclasses are defined in 'xxxtype.py' files.
    The instances of these subclasses are what the user sees as Python's
    type objects.  This class defines all general type-oriented behavior
    like attribute lookup and method resolution order.  Inheritance
    relationships are implemented *only* with the getbases() methods of
    W_TypeObject subclasses, *not* with interpreter-level inheritance between
    X_Xxx classes *nor* with multimethod delegation."""

    typename = None              # to be overridden by subclasses or instances
    #statictype = W_TypeType     (hacked into place below)
    staticbases = None           # defaults to (W_ObjectType,)

    def __init__(w_self, space):
        W_Object.__init__(w_self, space)
        w_self.w_tpname = space.wrap(w_self.typename)
        w_self.multimethods = {}
        # import all multimethods of the space and of the type class
        for multimethod in (hack_out_multimethods(space.__class__) +
                            hack_out_multimethods(w_self.__class__)):
            for i in range(len(multimethod.specialnames)):
                # each PyMultimethodCode bytecode is a (lazy, cached,
                # dynamically recomputed) slice of a multimethod.
                code = PyMultimethodCode(multimethod, i, w_self)
                w_self.multimethods[multimethod.specialnames[i]] = code

    def getbases(w_self):
        parents = w_self.staticbases
        if parents is None:
            import objecttype
            parents = (objecttype.W_ObjectType,)
        basetypes = [w_self.space.get_typeinstance(parent) for parent in parents]
        return tuple(basetypes)

    def getmro(w_self):
        # XXX this is something that works not too bad right now
        # XXX do the complete mro thing later
        mro = [w_self]
        for w_parent in w_self.getbases():
            mro += w_parent.getmro()
        return tuple(mro)

    def lookup(w_self, w_key):
        "XXX at some point, turn this into a multimethod"
        # note that this doesn't call __get__ on the result at all
        for w_class in w_self.getmro():
            try:
                return w_class.lookup_exactly_here(w_key)
            except KeyError:
                pass
        raise KeyError

    def lookup_exactly_here(w_self, w_key):
        space = w_self.space
        key = space.unwrap(w_key)
        assert isinstance(key, str)
        try:
            code = w_self.multimethods[key]
        except KeyError:
            raise KeyError   # pass on the KeyError
        if code.slice().is_empty():
            raise KeyError
        return space.newfunction(code, space.w_None, space.w_None)

    def acceptclass(w_self, cls):
        # For multimethod slicing. This checks whether a Python object of
        # type 'w_self' would be acceptable for a multimethod implementation
        # defined on the 'W_Xxx' class specified by 'cls'.
        # Currently implemented by following the 'statictype' attribute.
        # This results in operations defined on W_ObjectObject to be accepted,
        # but operations defined on W_ANY to be rejected.
        statictypeclass = cls.statictype
        if statictypeclass is not None:
            for w_parent in w_self.getmro():
                if isinstance(w_parent, statictypeclass):
                    return True
        return False


import typetype, objecttype
W_TypeObject.statictype = typetype.W_TypeType
registerimplementation(W_TypeObject)


def hack_out_multimethods(cls):
    return [value for value in cls.__dict__.itervalues()
                  if isinstance(value, MultiMethod)]


class PyMultimethodCode(pycode.PyBaseCode):

    def __init__(self, multimethod, bound_position, w_type):
        pycode.PyBaseCode.__init__(self)
        argnames = ['x%d'%(i+1) for i in range(multimethod.arity)]
        argnames.insert(0, argnames.pop(bound_position))
        self.co_name = multimethod.operatorsymbol
        self.co_flags = 0
        self.co_varnames = tuple(argnames)
        self.co_argcount = multimethod.arity
        self.basemultimethod = multimethod
        self.slicedmultimethod = None
        self.bound_position = bound_position
        self.w_type = w_type

    def cleardependency(self):
        # called when the underlying dispatch table is modified
        self.slicedmultimethod = None

    def slice(self):
        if self.slicedmultimethod is None:
            multimethod = self.basemultimethod
            print "pypy: slicing %r for a %r argument at position %d" % (
                multimethod.operatorsymbol,
                self.w_type.typename, self.bound_position)
            # slice the multimethod and cache the result
            sliced = multimethod.slicetable(self.bound_position, self.w_type)
            if sliced.is_empty():
                print "the slice is empty"
            self.slicedmultimethod = sliced.__get__(self.w_type.space, None)
            multimethod.cache_dependency(self)
        return self.slicedmultimethod

    def eval_code(self, space, w_globals, w_locals):
        """Call the multimethod, ignoring all implementations that do not
        have exactly the expected type at the bound_position."""
        multimethod = self.slice()
        dispatchargs = []
        initialtypes = []
        for i in range(multimethod.multimethod.arity):
            w_arg = space.getitem(w_locals, space.wrap('x%d'%(i+1)))
            dispatchargs.append(w_arg)
            initialtypes.append(w_arg.get_builtin_impl_class())
        dispatchargs = tuple(dispatchargs)
        initialtypes = tuple(initialtypes)
        try:
            w_result = multimethod.perform_call(dispatchargs, initialtypes)
        except FailedToImplement, e:
            if e.args:
                raise OperationError(*e.args)
            else:
                return space.w_NotImplemented
        except NoValue:
            raise OperationError(space.w_StopIteration, space.w_None)
        # XXX hack to accept real Nones from operations with no return value
        if w_result is None:
            w_result = space.w_None
        return w_result


def type_call(space, w_type, w_args, w_kwds):
    w_newobject = space.new(w_type, w_args, w_kwds)
    # XXX call __init__() later
    return w_newobject

StdObjSpace.call.register(type_call, W_TypeObject, W_ANY, W_ANY)


def type_issubtype(space, w_type1, w_type2):
    return space.newbool(w_type2 in w_type1.getmro())

StdObjSpace.issubtype.register(type_issubtype, W_TypeObject, W_TypeObject)
