from rpython.rlib import jit

class Signature(object):
    _immutable_ = True
    _immutable_fields_ = ["argnames[*]", "posonlyargnames[*]", "kwonlyargnames[*]"]
    __slots__ = ("argnames", "posonlyargnames", "kwonlyargnames", "varargname", "kwargname")

    def __init__(self, argnames, varargname=None, kwargname=None, kwonlyargnames=None, posonlyargnames=None):
        self.argnames = argnames
        self.varargname = varargname
        self.kwargname = kwargname
        if posonlyargnames is None:
            posonlyargnames = []
        self.posonlyargnames = posonlyargnames
        if kwonlyargnames is None:
            kwonlyargnames = []
        self.kwonlyargnames = kwonlyargnames

    @jit.elidable
    def find_argname(self, name):
        try:
            return self.posonlyargnames.index(name)
        except ValueError:
            pass
        try:
            return len(self.posonlyargnames) + self.argnames.index(name)
        except ValueError:
            pass
        try:
            return len(self.posonlyargnames) + len(self.argnames) + self.kwonlyargnames.index(name)
        except ValueError:
            pass
        return -1

    def num_argnames(self):
        return len(self.argnames)

    def num_posonlyargnames(self):
        return len(self.posonlyargnames)

    def num_kwonlyargnames(self):
        return len(self.kwonlyargnames)

    def has_vararg(self):
        return self.varargname is not None

    def has_kwarg(self):
        return self.kwargname is not None

    def scope_length(self):
        scopelen = len(self.argnames)
        scopelen += len(self.posonlyargnames)
        scopelen += len(self.kwonlyargnames)
        scopelen += self.has_vararg()
        scopelen += self.has_kwarg()
        return scopelen

    def getallvarnames(self):
        argnames = self.posonlyargnames
        argnames = argnames + self.argnames
        if self.varargname is not None:
            argnames = argnames + [self.varargname]
        argnames = argnames + self.kwonlyargnames
        if self.kwargname is not None:
            argnames = argnames + [self.kwargname]
        return argnames

    def __repr__(self):
        return "Signature(%r, %r, %r, %r, %r)" % (
                self.argnames, self.varargname, self.kwargname, self.kwonlyargnames, self.posonlyargnames)

    def __eq__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return (self.argnames == other.argnames and
                self.varargname == other.varargname and
                self.kwargname == other.kwargname and
                self.posonlyargnames == other.posonlyargnames and
                self.kwonlyargnames == other.kwonlyargnames)

    def __ne__(self, other):
        if not isinstance(other, Signature):
            return NotImplemented
        return not self == other
