from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec

import prolog.interpreter.term as pterm
import prolog.interpreter.signature as psig

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

    def __init__(self, space, term_p):
        # XXX typecheck
        # XXX should be p_term
        self.space = space
        self.term_p = term_p

    # properties
    def descr_len(self, space): return self.space.newint(self.term_p.argument_count())
    def prop_getname(self, space): return self.space.wrap(self.term_p.name()) # this is an interanal method name in pypy, I fear
    def prop_getargs(self, space):
        import pypy.module.unipycation.conversion as conv
        args = [ conv.w_of_p(self.space, x) for x in self.term_p.arguments() ]
        return self.space.newlist(args)

    def descr_getitem(self, space, w_idx):
        import pypy.module.unipycation.conversion as conv
        idx = self.space.int_w(w_idx)

        return conv.w_of_p(self.space, self.term_p.arguments()[idx])

    def descr_str(self, space):
        st = "Term(name=%s, len=%d)" % \
                (self.prop_getname(self.space), self.term_p.argument_count())
        return self.space.wrap(st)

W_Term.typedef = TypeDef("Term",
    __len__ = interp2app(W_Term.descr_len),
    __str__ = interp2app(W_Term.descr_str),
    __getitem__ = interp2app(W_Term.descr_getitem),
    __new__ = interp2app(term_new__),
    name = GetSetProperty(W_Term.prop_getname),
    args = GetSetProperty(W_Term.prop_getargs),
)

W_Term.typedef.acceptable_as_base_class = False
