from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, unwrap_spec
import pypy.module.unipycation.util as util
from pypy.interpreter.error import OperationError

import prolog.interpreter.term as pterm
import prolog.interpreter.signature as psig
import prolog.builtin.formatting as pfmt
import prolog.interpreter.continuation as pcont

from rpython.rlib import jit

#@unwrap_spec(name=str)
@jit.unroll_safe
def term_new__(space, w_subtype, w_name, w_args):
    from pypy.module.unipycation import conversion

    w_t = space.allocate_instance(W_CoreTerm, w_subtype)
    W_CoreTerm.__init__(w_t, space, w_name, w_args)
    return w_t

class W_CoreTerm(W_Root):
    """
    Represents a Callable from pyrolog
    """

    # Maybe later XXX
    #_immutable_fields_ = ["w_name", "w_args"]

    def __init__(self, space, w_name, w_args):
        self.space = space
        self.w_args = w_args
        self.w_name = w_name # not actually wrapped!

    # properties
    def descr_len(self, space): return self.space.newint(self.w_args.length())
    def prop_getname(self, space): return self.w_name
    def prop_getargs(self, space): return self.w_args

    def descr_getitem(self, space, w_idx):
        if not space.is_true(space.isinstance(w_idx, space.w_int)):
            raise OperationError(space.w_IndexError, space.wrap("bad argument index"))

        el = space.finditem(self.w_args, w_idx)
        if el is None:
            raise OperationError(space.w_IndexError, space.wrap("bad argument index"))
        return el

    def descr_eq(self, space, w_other):
        if not space.eq_w(space.type(self), space.type(w_other)):
            return space.w_False
        other = space.interp_w(W_CoreTerm, w_other)
        return space.w_True if self.w_args == other.w_args else space.w_False

    def descr_ne(self, space, w_other):
        return space.not_(self.descr_eq(space, w_other))

    def descr_str(self, space):
        args_strs = []
        for i in range(space.len_w(self.w_args)):
            x = space.finditem(self.w_args, space.wrap(i))
            args_strs.append(space.str_w(space.call_method(x, "__str__")))
        return space.wrap("%s(%s)" % (space.str_w(self.w_name), ", ".join(args_strs)))

    # XXX repr is not very consistent.
    # Integers and stuff in args will print the interp-level wrapper instance.
    def descr_repr(self, space):
        return space.wrap("%s(%s, %s)" % (
                space.type(self).getname(space),
                space.str_w(space.repr(self.w_name)),
                space.str_w(space.repr(self.prop_getargs(space))),
                ))

    @staticmethod
    def _from_term(space, w_subtype, w_term):
        if not isinstance(w_term, W_CoreTerm):
            raise OperationError(space.w_TypeError, space.wrap("need a CoreTerm"))
        w_result = space.allocate_instance(W_CoreTerm, w_subtype)
        W_CoreTerm.__init__(w_result, space, w_term.w_name, w_term.w_args)
        return w_result


W_CoreTerm.typedef = TypeDef("CoreTerm",
    __eq__ = interp2app(W_CoreTerm.descr_eq),
    __getitem__ = interp2app(W_CoreTerm.descr_getitem),
    __len__ = interp2app(W_CoreTerm.descr_len),
    __ne__ = interp2app(W_CoreTerm.descr_ne),
    __new__ = interp2app(term_new__),
    __str__ = interp2app(W_CoreTerm.descr_str),
    __repr__ = interp2app(W_CoreTerm.descr_repr),
    args = GetSetProperty(W_CoreTerm.prop_getargs),
    name = GetSetProperty(W_CoreTerm.prop_getname),
    _from_term = interp2app(W_CoreTerm._from_term, as_classmethod=True),
)

# ---

def var_new__(space, w_subtype, __args__): # __args__ unused
    return W_Var(space)

class W_Var(W_Root):
    """
    Represents an unbound variable in a query.
    """

    NEXT_UNIQUE = 0
    _UNIQUE_PREFIX = "_V"

    def __init__(self, space):
        self.space = space
        # just for the sake of printing a variable, give it a name.
        self.w_name = space.wrap("%s%d" % (W_Var._UNIQUE_PREFIX, W_Var.NEXT_UNIQUE))
        W_Var.NEXT_UNIQUE += 1

    # XXX broken
    #@classmethod
    #def descr_unique_prefix(cls, space):
    #    return space.wrap(W_Var._UNIQUE_PREFIX)

    def descr_str(self, space): return self.w_name
    def descr_repr(self, space):
        return space.wrap("Var(%s)" % repr(space.str_w(self.w_name)))

W_Var.typedef = TypeDef("Var",
    __new__ = interp2app(var_new__),
    __str__ = interp2app(W_Var.descr_str),
    __repr__ = interp2app(W_Var.descr_repr),
    #UNIQUE_PREFIX = GetSetProperty(W_Var.descr_unique_prefix),
    #UNIQUE_PREFIX = interp2app(W_Var.descr_unique_prefix, as_classmethod=True),
)

W_Var.typedef.acceptable_as_base_class = False
