from pypy.interpreter import pycode
from pypy.objspace.std.objspace import *


class W_TypeObject(W_AbstractTypeObject):
    """This class is abstract.  Subclasses are defined in 'xxxtype.py' files.
    The instances of these subclasses are what the user sees as Python's
    type objects.  This class defines all general type-oriented behavior
    like attribute lookup and method resolution order.  Inheritance
    relationships are implemented *only* with the getbases() methods of
    W_TypeObject subclasses, *not* with interpreter-level inheritance between
    W_Xxx classes *nor* with multimethod delegation."""

    typename = None              # to be overridden by subclasses or instances
    #statictype = W_TypeType     (hacked into place below)
    staticbases = None           # defaults to (W_ObjectType,)

    def __init__(w_self, space):
        W_Object.__init__(w_self, space)
        w_self.w_tpname = space.wrap(w_self.typename)
        w_self.multimethods = {}
        # import all multimethods of the type class and of the objspace
        for multimethod in (hack_out_multimethods(w_self.__class__) +
                            hack_out_multimethods(space.__class__)):
            for i in range(len(multimethod.specialnames)):
                # each PyMultimethodCode embeds a multimethod
                name = multimethod.specialnames[i]
                code = PyMultimethodCode(multimethod, w_self.__class__, i)
                w_self.multimethods[name] = code

    def getbases(w_self):
        parents = w_self.staticbases
        if parents is None:
            # Note: this code is duplicated in multimethod.py
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
        # note that this doesn't call __get__ on the result at all
        # XXX this should probably also return the (parent) class in which
        # the attribute was found
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
        return space.newfunction(code, space.w_None, code.getdefaults(space))


import typetype, objecttype
W_TypeObject.statictype = typetype.W_TypeType
registerimplementation(W_TypeObject)


def hack_out_multimethods(cls):
    result = []
    for base in cls.__bases__:
        result += hack_out_multimethods(base)
    for value in cls.__dict__.itervalues():
        if isinstance(value, MultiMethod):
            result.append(value)
    return result


class PyMultimethodCode(pycode.PyBaseCode):

    def __init__(self, multimethod, typeclass, bound_position=0):
        pycode.PyBaseCode.__init__(self)
        argnames = ['x%d'%(i+1) for i in range(multimethod.arity)]
        argnames.insert(0, argnames.pop(bound_position))
        self.co_name = multimethod.operatorsymbol
        self.co_flags = 0
        self.co_varnames = tuple(argnames)
        self.co_argcount = multimethod.arity
        self.basemultimethod = multimethod
        self.typeclass = typeclass
        self.bound_position = bound_position

    def getdefaults(self, space):
        return space.wrap(self.basemultimethod.defaults)

    def slice(self):
        return self.basemultimethod.slice(self.typeclass, self.bound_position)

    def eval_code(self, space, w_globals, w_locals):
        """Call the multimethod, ignoring all implementations that do not
        have exactly the expected type at the bound_position."""
        multimethod = self.slice()
        dispatchargs = []
        for i in range(multimethod.arity):
            w_arg = space.getitem(w_locals, space.wrap('x%d'%(i+1)))
            dispatchargs.append(w_arg)
        dispatchargs = tuple(dispatchargs)
        try:
            w_result = multimethod.get(space).perform_call(dispatchargs)
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


def call__Type_ANY_ANY(space, w_type, w_args, w_kwds):
    w_newobject = space.new(w_type, w_args, w_kwds)
    # XXX call __init__() later
    return w_newobject

def issubtype__Type_Type(space, w_type1, w_type2):
    return space.newbool(w_type2 in w_type1.getmro())

def repr__Type(space, w_obj):
    return space.wrap("<type '%s'>" % w_obj.typename) 

def getattr__Type_ANY(space, w_type, w_attr):
    # XXX mwh doubts this is the Right Way to do this...
    if space.is_true(space.eq(w_attr, space.wrap('__name__'))):
        return w_type.w_tpname
    if space.is_true(space.eq(w_attr, space.wrap('__mro__'))):
        return space.newtuple(list(w_type.getmro()))
    raise FailedToImplement


register_all(vars())
