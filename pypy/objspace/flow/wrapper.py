# ______________________________________________________________________
"""Wrapper objects for the control flow analysis object space."""
# ______________________________________________________________________

# This is kinda a hack, but at the same time, I don't see why this was defined
# in the object space module in the annotation object space.

class UnwrapException(Exception):
    pass

# ______________________________________________________________________

class W_Object(object):
    """Abstract base class.  do not instantiate."""

    force  = None # See cloningcontext.py

    def __new__(cls, *args, **kwd):
        assert cls is not W_Object
        return object.__new__(cls)

    def __init__(self):
        pass

    def __repr__(self):
        s = self.argsrepr()
        if len(s) > 100:
            s = s[:25] + "..." + s[-25:]
        return "%s(%s)" % (self.__class__.__name__, s)

    def argsrepr(self):
        return ""

    def unwrap(self):
        # XXX Somehow importing this at module level doesn't work
        raise UnwrapException(self)

    def __eq__(self, other):
        return type(other) is type(self)

    def __ne__(self, other):
        return not self.__eq__(other)

# ______________________________________________________________________

class W_Variable(W_Object):
    pass

# ______________________________________________________________________

class W_Constant(W_Object):
    """A specific constant value."""

    def __init__(self, value):
        self.value = value

    def argsrepr(self):
        return repr(self.value)

    def unwrap(self):
        return self.value

    def __eq__(self, other):
        return type(other) is type(self) and self.value == other.value

    def __len__(self):
        return len(self.value)

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

# ______________________________________________________________________
# End of wrapper.py
