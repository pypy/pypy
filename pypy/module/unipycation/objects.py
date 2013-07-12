from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec

import prolog.interpreter.term as pterm
import prolog.interpreter.signature as psig
import pypy.module.unipycation.util as util

@unwrap_spec(name=str)
def term_new__(space, w_subtype, name, __args__):
    import pypy.module.unipycation.conversion as conv
    w_args = __args__.unpack()[0][0]

    # collect args for prolog Term constructor
    term_args = [ conv.p_of_w(space, w_x) for w_x in space.listview(w_args) ]
    p_sig = psig.Signature.getsignature(name, len(term_args))
    p_term = pterm.Term(name, term_args, p_sig)

    return W_Term(space, p_term)

class W_Term(W_Root):
    """
    Represents a Callable from pyrolog
    """

    def __init__(self, space, p_term):
        self.space = space
        self.p_term = p_term

    # properties
    def descr_len(self, space): return self.space.newint(self.p_term.argument_count())
    def prop_getname(self, space): return self.space.wrap(self.p_term.name()) # this is an interanal method name in pypy, I fear
    def prop_getargs(self, space):
        import pypy.module.unipycation.conversion as conv
        args = [ conv.w_of_p(self.space, x) for x in self.p_term.arguments() ]
        return self.space.newlist(args)

    def descr_getitem(self, space, w_idx):
        import pypy.module.unipycation.conversion as conv
        idx = self.space.int_w(w_idx)

        return conv.w_of_p(self.space, self.p_term.arguments()[idx])

    def descr_str(self, space):
        st = "Term(name=%s, len=%d)" % \
                (self.prop_getname(self.space), self.p_term.argument_count())
        return self.space.wrap(st)

    def descr_eq(self, space, w_other):
        w_Term = util.get_from_module(self.space, "unipycation", "Term")

        if not space.is_true(space.isinstance(w_other, w_Term)):
            return space.w_False

        eq = self.p_term.cmp_standard_order(w_other.p_term, None)
        return space.wrap(eq == 0)

    def descr_ne(self, space, w_other):
        return space.not_(self.descr_eq(space, w_other))

    def descr_str(self, space):
        args_strs = [ str(x) for x in self.p_term.arguments() ]
        args_str = ", ".join(args_strs)
        return space.wrap("%s(%s)" % (self.p_term.name(), args_str))

W_Term.typedef = TypeDef("Term",
    __eq__ = interp2app(W_Term.descr_eq),
    __getitem__ = interp2app(W_Term.descr_getitem),
    __len__ = interp2app(W_Term.descr_len),
    __ne__ = interp2app(W_Term.descr_ne),
    __new__ = interp2app(term_new__),
    __str__ = interp2app(W_Term.descr_str),
    args = GetSetProperty(W_Term.prop_getargs),
    name = GetSetProperty(W_Term.prop_getname),
)

W_Term.typedef.acceptable_as_base_class = False

# ---

def var_new__(space, w_subtype, __args__): # __args__ unused
    p_var = pterm.BindingVar()
    return W_Var(space, p_var)

class W_Var(W_Root):
    """
    Represents an unbound variable in a query.
    """
    var_ct = 0  # Used to build a unique id name for each var

    def __init__(self, space, p_var):
        self.space = space
        self.p_var = p_var
        self.w_name = space.wrap("V%d" % W_Var.var_ct)
        W_Var.var_ct += 1

    def descr_str(self, space): return self.w_name

W_Var.typedef = TypeDef("Var",
    __new__ = interp2app(var_new__),
    __str__ = interp2app(W_Var.descr_str),
)

W_Var.typedef.acceptable_as_base_class = False
