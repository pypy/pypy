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

@unwrap_spec(name=str)
@jit.unroll_safe
def term_new__(space, w_subtype, name, w_args):
    from pypy.module.unipycation import conversion

    # collect args for prolog Term constructor
    term_args = [ conversion.p_of_w(space, w_x) for w_x in space.listview(w_args) ]
    p_sig = psig.Signature.getsignature(name, len(term_args))
    p_term = pterm.Callable.build(name, term_args, p_sig)

    w_t = space.allocate_instance(W_CoreTerm, w_subtype)
    W_CoreTerm.__init__(w_t, space, p_term)

    return w_t

class W_CoreTerm(W_Root):
    """
    Represents a Callable from pyrolog
    """

    _immutable_fields_ = ["p_term"]

    def __init__(self, space, p_term):
        self.space = space
        self.p_term = p_term

    # properties
    def descr_len(self, space): return self.space.newint(self.p_term.argument_count())
    def prop_getname(self, space): return self.space.wrap(self.p_term.name()) # this is an interanal method name in pypy, I fear
    def prop_getargs(self, space):
        from pypy.module.unipycation import conversion
        args = [ conversion.w_of_p(self.space, x) for x in self.p_term.arguments() ]
        return self.space.newlist(args)

    def descr_getitem(self, space, w_idx):
        from pypy.module.unipycation import conversion
        idx = self.space.int_w(w_idx)
        p_term = self.p_term
        length = p_term.argument_count()
        if idx >= length:
            raise OperationError(space.w_IndexError, space.wrap("index out of bounds"))
        if idx < 0:
            idx += length
            if idx < 0:
                raise OperationError(space.w_IndexError, space.wrap("index out of bounds"))
        return conversion.w_of_p(self.space, p_term.argument_at(idx))

    def descr_eq(self, space, w_other):
        #w_CoreTerm = util.get_from_module(self.space, "unipycation", "CoreTerm")

        if not space.eq_w(space.type(self), space.type(w_other)):
            return space.w_False
        w_other = space.interp_w(W_CoreTerm, w_other)

        eq = self.p_term.cmp_standard_order(w_other.p_term, None)
        return space.wrap(eq == 0)

    def descr_ne(self, space, w_other):
        return space.not_(self.descr_eq(space, w_other))

    def descr_str(self, space):
        # XXX Hackarama XXX.
        # TermFormatter needs an engine, so we just make a new one.
        tmp_engine = pcont.Engine()
        fmtr = pfmt.TermFormatter(tmp_engine)
        return space.wrap(fmtr.format(self.p_term))

    def descr_repr(self, space):
        name = space.str_w(space.repr(space.wrap(self.p_term.signature().name)))
        argsstr = space.str_w(space.repr(self.prop_getargs(space)))
        res = "%s(%s, %s)" % (space.type(self).getname(space), name, argsstr)
        return space.wrap(res)


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
)


# ---

def var_new__(space, w_subtype, __args__): # __args__ unused
    p_var = pterm.BindingVar()
    return W_Var(space, p_var)

class W_Var(W_Root):
    """
    Represents an unbound variable in a query.
    """
    _immutable_fields_ = ["p_var"]

    def __init__(self, space, p_var):
        self.space = space
        self.p_var = p_var

    def descr_str(self, space):

        # XXX Hackarama XXX.
        # TermFormatter needs an engine, so we just make a new one.
        tmp_engine = pcont.Engine()
        fmtr = pfmt.TermFormatter(tmp_engine)
        return self.space.wrap(fmtr.format(self.p_var))

W_Var.typedef = TypeDef("Var",
    __new__ = interp2app(var_new__),
    __str__ = interp2app(W_Var.descr_str),
)

W_Var.typedef.acceptable_as_base_class = False
