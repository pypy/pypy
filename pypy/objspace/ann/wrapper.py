"""Wrapper objects used by annotating space.

The classes here represent various amounts of knowledge about a
wrapped object, from W_Constant (we know the exact value) to
W_Anything (we know nothing).  The union() function computes unions.
We expect that there will eventually be a class that represents a
union of constants or other types too, in some cases.

"""

class W_Object(object):
    pass

class W_Anything(W_Object):
    pass

class W_Integer(W_Object):
    pass

class W_Constant(W_Object):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return '<constant %r>' % self.value

class W_KnownKeysContainer(W_Object):
    def __init__(self, args_w):
        self.args_w = args_w
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

def union(r1, r2):
    # Unite two results
    if r1 is r2:
        return r1
    if r1 is None:
        return r2
    if r2 is None:
        return r1
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
    return (isinstance(w_obj, W_Integer) or
            isinstance(w_obj, W_Constant) and isinstance(w_obj.value, int))
