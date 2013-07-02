from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app

class W_Term(W_Root):
    """
    Represents an aggregate term from pyrolog
    """

    def __init__(self, space, term_p):
        self.space = space
        self.term_p = term_p

    # properties
    def getlength(self): return self.space.newint(self.term_p.argument_count())
    def getname(self): return self.space.wrap(self.term_p.name())
    def getargs(self):
        import pypy.module.unipycation.conversion as conv
        args = [ conv.w_of_p(self.space, x) for x in self.term_p.arguments() ]
        return self.space.newlist(args)

W_Term.typedef = TypeDef("Term",
    #__len__ = interp2app(W_Term.len_w),
    length = GetSetProperty(W_Term.getlength),
    name = GetSetProperty(W_Term.getname),
    args = GetSetProperty(W_Term.getargs),
)

