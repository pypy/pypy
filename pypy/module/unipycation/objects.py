from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app

class W_Term(W_Root):
    """
    Represents a Callable from pyrolog
    """

    def __init__(self, space, term_p):
        self.space = space
        self.term_p = term_p

    # properties
    def prop_getlength(self, space): return self.space.newint(self.term_p.argument_count())
    def prop_getname(self, space): return self.space.wrap(self.term_p.name()) # this is an interanal method name in pypy, I fear
    def prop_getargs(self, space):
        import pypy.module.unipycation.conversion as conv
        args = [ conv.w_of_p(self.space, x) for x in self.term_p.arguments() ]
        return self.space.newlist(args)

W_Term.typedef = TypeDef("Term",
    length = GetSetProperty(W_Term.prop_getlength),
    name = GetSetProperty(W_Term.prop_getname),
    args = GetSetProperty(W_Term.prop_getargs),
)

