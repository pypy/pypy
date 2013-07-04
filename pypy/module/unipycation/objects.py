from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app

# XXX may be useful for listifying a cons
"""
def decons(t):
    print("DECONS: %s" % str(t))
    if not isinstance(t, unipycation.Term) or t.name != ".":
        raise TypeError("Bad cons, should not happen")

    print("CAR (%s): %s   CDR (%s): %s\n" % (type(t[0]), t[0], type(t[1]), t[1]))

    (car, cdr) = (t[0], t[1])

    if isinstance(cdr, unipycation.Term):
        # more unwrapping to do
        if cdr.name != ".": raise TypeError("Bad Cons (2), should not happen")
        return [car] + decons(cdr)
    elif cdr == "[]": # Seems the empty list is an atom
        return [car]
    else:
        raise TypeError("This should not happen")
"""

def decons_idx(space, t, idx):
    """ Recurse a prolog Cons looking for the element at index 'idx' """

    # XXX type check
    (car, cdr) = t.arguments() # should be only ever 2 elems

    if idx != 0:
        # XXX type check.
        # XXX index out of bounds case (find [] in cdr)
        if cdr.signature().name != ".":
                raise TypeError("Bad Cons! Should not happen")

        return decons_idx(space, cdr, idx - 1)
    else:
        # found the desired index
        return car

class W_Term(W_Root):
    """
    Represents a Callable from pyrolog
    """

    def __init__(self, space, term_p):
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

        if self.space.str_w(self.prop_getname(self.space)) == ".":
            # Need to walk the cons
            return conv.w_of_p(self.space, decons_idx(self.space, self.term_p, idx))
        else:
            # Otherwise, straightforward indexing
            return conv.w_of_p(self.space, self.term_p.arguments()[idx])

    def descr_str(self, space):
        st = "Term(name=%s, len=%d)" % \
                (self.prop_getname(self.space), self.term_p.argument_count())
        return self.space.wrap(st)

W_Term.typedef = TypeDef("Term",
    __len__ = interp2app(W_Term.descr_len),
    __str__ = interp2app(W_Term.descr_str),
    __getitem__ = interp2app(W_Term.descr_getitem),
    name = GetSetProperty(W_Term.prop_getname),
    args = GetSetProperty(W_Term.prop_getargs),
)

