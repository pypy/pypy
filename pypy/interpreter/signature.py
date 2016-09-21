from rpython.rlib import jit

class Signature(object):
    _immutable_fields_ = ["argnames[*]", "varargname", "kwargname"]
    __slots__ = ("argnames", "varargname", "kwargname")

    def __init__(self, argnames, varargname=None, kwargname=None):
        self.argnames = argnames
        self.varargname = varargname
        self.kwargname = kwargname

    @jit.elidable
    def find_argname(self, name):
        try:
            return self.argnames.index(name)
        except ValueError:
            return -1

    def num_argnames(self):
        return len(self.argnames)

    def has_vararg(self):
        return self.varargname is not None

    def has_kwarg(self):
        return self.kwargname is not None

    def scope_length(self):
        scopelen = len(self.argnames)
        scopelen += self.has_vararg()
        scopelen += self.has_kwarg()
        return scopelen

    def getallvarnames(self):
        argnames = self.argnames
        if self.varargname is not None:
            argnames = argnames + [self.varargname]
        if self.kwargname is not None:
            argnames = argnames + [self.kwargname]
        return argnames

    def __repr__(self):
        return "Signature(%r, %r, %r)" % (
                self.argnames, self.varargname, self.kwargname)

    def __eq__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return (self.argnames == other.argnames and
                self.varargname == other.varargname and
                self.kwargname == other.kwargname)

    def __ne__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return not self == other
