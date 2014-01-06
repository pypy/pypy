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

@jit.unroll_safe
def term_new__(space, w_subtype, w_name, w_args):
    from pypy.module.unipycation import conversion

    w_t = space.allocate_instance(W_CoreTerm, w_subtype)
    args_w = space.unpackiterable(w_args)
    W_CoreTerm.__init__(w_t, space, w_name, args_w)
    return w_t

class W_CoreTerm(W_Root):
    """
    Represents a Callable from pyrolog
    """

    # Maybe later XXX
    #_immutable_fields_ = ["w_name", "args_w[*]"]

    def __init__(self, space, w_name, args_w):
        self.space = space
        self.args_w = args_w
        self.w_name = w_name # not actually wrapped!

    # properties
    def descr_len(self, space): return self.space.newint(len(self.args_w))
    def prop_getname(self, space): return self.w_name
    def prop_getargs(self, space): return space.newlist(list(self.args_w))

    def descr_getitem(self, space, w_idx):
        index = space.getindex_w(w_idx, space.w_IndexError, "term index")
        try:
            return self.args_w[index]
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("term index out of range"))


    def descr_eq(self, space, w_other):
        if not space.eq_w(space.type(self), space.type(w_other)):
            return space.w_False
        assert isinstance(w_other, W_CoreTerm)
        if len(self.args_w) != len(w_other.args_w):
            return space.w_False
        for i, w_arg in enumerate(self.args_w):
            if not space.eq_w(w_arg, w_other.args_w[i]):
                return space.w_False
        return space.w_True

    def descr_ne(self, space, w_other):
        return space.not_(self.descr_eq(space, w_other))

    def descr_str(self, space):
        args_strs = []
        for i, w_arg in enumerate(self.args_w):
            args_strs.append(space.str_w(space.str(w_arg)))
        return space.wrap("%s(%s)" % (space.str_w(self.w_name), ", ".join(args_strs)))

    def descr_repr(self, space): return self.descr_str(space)

    @staticmethod
    def _from_term(space, w_subtype, w_term):
        if not isinstance(w_term, W_CoreTerm):
            raise OperationError(space.w_TypeError, space.wrap("need a CoreTerm"))
        w_result = space.allocate_instance(W_CoreTerm, w_subtype)
        W_CoreTerm.__init__(w_result, space, w_term.w_name, w_term.args_w)
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

    def __init__(self, space, p_var=None):
        self.space = space
        self.p_var = p_var if p_var is not None else pterm.BindingVar()

    def descr_str(self, space):
        # XXX Hackarama XXX.
        # TermFormatter needs an engine, so we just make a new one.
        tmp_engine = pcont.Engine()
        fmtr = pfmt.TermFormatter(tmp_engine)
        return self.space.wrap(fmtr.format(self.p_var))

    def descr_repr(self, space): return self.descr_str(space)

W_Var.typedef = TypeDef("Var",
    __new__ = interp2app(var_new__),
    __str__ = interp2app(W_Var.descr_str),
    __repr__ = interp2app(W_Var.descr_repr),
)

W_Var.typedef.acceptable_as_base_class = False
