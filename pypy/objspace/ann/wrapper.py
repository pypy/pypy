"""Wrapper objects used by annotating space.

The classes here represent various amounts of knowledge about a
wrapped object, from W_Constant (we know the exact value) to
W_Anything (we know nothing).  The union() function computes unions.
We expect that there will eventually be a class that represents a
union of constants or other types too, in some cases.

"""

import copy

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
        from pypy.objspace.ann.objspace import UnwrapException
        raise UnwrapException(self)

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

    def clone(self):
        if type(self.value) is type(lambda:0): # XXX
            return W_Constant(self.value)
        try:
            return W_Constant(copy.deepcopy(self.value))
        except TypeError:
            return W_Constant(self.value)
        except:
            return W_Constant(self.value)


class W_KnownKeysContainer(W_Object):
    """A dict with a known set of keys or a list with known length.

    XXX This is mutable!  Is that a good idea?

    XXX Should unify some of this with W_Constant.
    """

    def __init__(self, args_w):
        self.args_w = args_w

    def argsrepr(self):
        return repr(self.args_w)

    def unwrap(self):
        if hasattr(self.args_w, "keys"):
            d = {}
            for k, w_v in self.args_w.iteritems():
                d[k] = w_v.unwrap()
            return d
        assert isinstance(self.args_w, list), self.args_w
        l = []
        for w_obj in self.args_w:
            l.append(w_obj.unwrap())
        return l

    def __eq__(self, other):
        return type(other) is type(self) and self.args_w == other.args_w

    def __len__(self):
        return len(self.args_w)

    def __getitem__(self, key):
        return self.args_w[key]

    def __setitem__(self, key, w_value):
        self.args_w[key] = w_value

    def clone(self):
        args_w = self.args_w
        if isinstance(args_w, dict):
            args_w = args_w.copy()
        return W_KnownKeysContainer(args_w)

class W_ConstantIterator(W_Object):

    def __init__(self, seq, start=0): # XXX should we copy seq, and roll our own definition of identity?
        self.seq = seq
        self.start = start

    def argsrepr(self):
        return "%r, %r" % (self.seq, self.start)

    def __eq__(self,other):
        return type(self) is type(other) and self.seq is other.seq and self.start == other.start

    def clone(self):
        return W_ConstantIterator(self.seq, self.start)

    def next(self):
        try:
            value = self.seq[self.start]
        except IndexError:
            raise StopIteration
        self.changed = True
        self.start += 1
        return value

class W_Module(W_Object):
    """A module object.  It supports getattr and setattr (yikes!)."""

    def __init__(self, w_name, w_doc):
        # The wrapped module name and wrapped docstring must be known
        self.w_name = w_name
        self.w_doc = w_doc
        self.w_dict = W_KnownKeysContainer({"__name__": w_name,
                                            "__doc__": w_doc})

    def argsrepr(self):
        return repr(self.w_name) + ", " + repr(self.w_doc)

    def getattr(self, name):
        # Returned a wrapped object or raise an unwrapped KeyError exception
        if name == "__dict__":
            return self.w_dict
        return self.w_dict[name]

    def setattr(self, name, w_obj):
        self.w_dict.args_w[name] = w_obj

class W_BuiltinFunction(W_Object):
    """A function that executes in interpreter space."""

    def __init__(self, code, w_defaults):
        self.code = code
        self.w_defaults = w_defaults

    def argsrepr(self):
        return repr(self.code) + ", " + repr(self.w_defaults)

class W_PythonFunction(W_Object):
    """A Python function."""

    def __init__(self, code, w_globals, w_defaults, w_closure=None):
        self.code = code
        self.w_globals = w_globals
        self.w_defaults = w_defaults
        self.w_closure = w_closure

    def argsrepr(self):
        s = repr(self.code) + ", " + repr(self.w_globals)
        s += ", " + repr(self.w_defaults)
        if self.w_closure != None:
            s += ", " + repr(self.w_closure)
        return s

    

def unify_frames(f1, f2):
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
        u = union(v1, v2)
        if v1 != u:
            c1 = True
            s1[i] = u
        if v2 != u:
            c2 = True
            s2[i] = u

    # Compare locals.
    # XXX This uses the fast locals now and ignores w_locals.
    # XXX What about nested cells?
    l1 = f1.localcells
    l2 = f2.localcells
    assert len(l1) == len(l2)
    for i in range(len(l1)):
        try:
            v1 = l1[i].get()
        except ValueError:
            v1 = W_Undefined()
        try:
            v2 = l2[i].get()
        except ValueError:
            v2 = W_Undefined()
        u = union(v1, v2)
        if v1 != u:
            c1 = True
            l1[i].set(u)
        if v2 != u:
            c2 = True
            l2[i].set(u)

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
            len(f1.localcells) == len(f2.localcells) and
            len(f1.nestedcells) == len(f2.nestedcells) and
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
    if (isinstance(r1, W_ConstantIterator) and
        isinstance(r2, W_ConstantIterator) and
        r1.seq is r2.seq):
        return W_ConstantIterator(r1.seq,max(r1.start,r2.start))
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
