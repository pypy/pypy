"""Wrapper objects used by annotating space.

The classes here represent various amounts of knowledge about a
wrapped object, from W_Constant (we know the exact value) to
W_Anything (we know nothing).  The union() function computes unions.
We expect that there will eventually be a class that represents a
union of constants or other types too, in some cases.

"""

class W_Object(object):
    """Abstract base class.  do not instantiate."""
    def __new__(cls, *args, **kwd):
        assert cls is not W_Object
        return object.__new__(cls)
    def __init__(self):
        pass
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.argsrepr())
    def argsrepr(self):
        return ""
    def __eq__(self, other):
        return type(other) is type(self)
    def __ne__(self, other):
        return not self.__eq__(other)

class W_Undefined(W_Object):
    """May be undefined.  This is the most contagious type."""
    pass

class W_Anything(W_Object):
    """Any (defined) value.   This is the next most contagious type."""
    pass

class W_Integer(W_Object):
    """An integer value (int or long)."""
    pass

class W_Constant(W_Object):
    """A specific constant value."""
    def __init__(self, value):
        self.value = value
    def argsrepr(self):
        return repr(self.value)[:50]
    def __eq__(self, other):
        return type(other) is type(self) and self.value == other.value

class W_KnownKeysContainer(W_Object):
    """A dict with constant set of keys or a tuple with known length."""
    def __init__(self, args_w):
        self.args_w = args_w
    def argsrepr(self):
        return repr(self.args_w)
    def __eq__(self, other):
        return type(other) is type(self) and self.args_w == other.args_w
    def __len__(self):
        return len(self.args_w)
    def __getitem__(self, i):
        return self.args_w[i]
    def clone(self):
        args_w = self.args_w
        if isinstance(args_w, dict):
            args_w = args_w.copy()
        # XXX Recurse down the values?
        return W_KnownKeysContainer(args_w)

def unite_frames(f1, f2):
    """Given two compatible frames, make them the same.

    This changes both f1 and f2 in-place to change all the values into
    their union.  It returns two booleans, indicating whether the
    frames were changed.

    This requires that the frames are compatible.

    """
    assert compatible_frames(f1, f2)

    # Compare value stacks
    # XXX uses stack internals
    s1 = f1.valuestack.items
    s2 = f2.valuestack.items
    c1 = c2 = False # changed flags
    n = len(s1)
    assert n == len(s2)
    for i in range(n):
        v1 = s1[i]
        v2 = s2[i]
        if v1 != v2:
            u = union(v1, v2)
            if v1 != u:
                c1 = True
                s1[i] = u
            if v2 != u:
                c2 = True
                s2[i] = u

    # Compare locals
    # XXX uses W_KnownKeysContainer internals
    assert isinstance(f1.w_locals, W_KnownKeysContainer)
    assert isinstance(f2.w_locals, W_KnownKeysContainer)
    l1 = f1.w_locals.args_w
    l2 = f2.w_locals.args_w
    keydict = {} # compute set of keys
    for key in l1.iterkeys():
        keydict[key] = 1
    for key in l2.iterkeys():
        keydict[key] = 1
    for key in keydict.iterkeys():
        v1 = l1.get(key, W_Undefined())
        v2 = l2.get(key, W_Undefined())
        u = union(v1, v2)
        if v1 != u:
            c1 = True
            l1[key] = u
        if v2 != u:
            c2 = True
            l2[key] = u
    return c1, c2

def compatible_frames(f1, f2):
    """Return whether two frames are compatible.

    Informally, this means that they represent different states
    at the same point in the program.

    """
    if f1 is f2:
        return True
    return (f1.next_instr == f2.next_instr and
            f1.space is f2.space and
            f2.bytecode is f2.bytecode and
            f1.valuestack.depth() == f2.valuestack.depth() and
            equivalent(f1.w_globals, f2.w_globals) and
            equivalent(f1.w_builtins, f2.w_builtins) and
            f1.blockstack.items == f2.blockstack.items)

def equivalent(w1, w2):
    """Return whether two wrappers are equivalent

    (Helper for compatible_frames.)

    They must be constant wrappers for the same object.

    """
    return (isinstance(w1, W_Constant) and
            isinstance(w2, W_Constant) and
            w1.value is w2.value)

def union(r1, r2):
    """Return the union of two wrappers."""
    if r1 is r2:
        return r1
    if r1 is None:
        return r2
    if r2 is None:
        return r1
    if isinstance(r1, W_Undefined) or isinstance(r2, W_Undefined):
        return W_Undefined()
    if isinstance(r1, W_Anything) or isinstance(r2, W_Anything):
        return W_Anything()
    if (isinstance(r1, W_Constant) and isinstance(r2, W_Constant) and
        r1.value == r2.value):
        return W_Constant(r1.value)
    if is_int(r1) and is_int(r2):
        return W_Integer()
    if (isinstance(r1, W_KnownKeysContainer) and
        isinstance(r2, W_KnownKeysContainer) and
        r1.args_w == r2.args_w):
        return W_KnownKeysContainer(r1.args_w)
    # XXX Could do more cases.
    # XXX This will blow up as we add more types.  Refactor when that happens.
    return W_Anything()

def is_int(w_obj):
    """Return whether a wrapped object is an integer.

    It could either be W_Integer or an constant integer.
    """
    return (isinstance(w_obj, W_Integer) or
            (isinstance(w_obj, W_Constant) and
             isinstance(w_obj.value, (int, long))))
