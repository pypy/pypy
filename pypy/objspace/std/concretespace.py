# I (mwh) wanted to get some stuff out of objspace.py

# this file is intended to contain implementations of most of the
# "concrete objects" layer of the Python/C API

# the idea is, roughly, e.g.:
#
# PyInt_FromLong -> space.int.from_long(w_int)
# PyList_GetItem -> space.list.getitem(w_list, i)
#
# etc.

# I'm not sure this is a good idea.

class ConcreteSpace(object):
    __slots__ = ['space']
    def __init__(self, space):
        self.space = space

class IntObjSpace(ConcreteSpace):
    __slots__ = []
    def check(self, ob):
        return isinstance(ob, self.space.W_IntObject)
    def check_exact(self, ob):
        return ob.__class__ is self.space.W_IntObject
    def from_string(self, s, base):
        return self.from_long(int(s, base))
    def from_unicode(self, u, base):
        return self.from_long(int(u, base))
    def from_long(self, l):
        return self.space.W_IntObject(l)
    def as_long(self, w_int):
        if self.check(w_int):
            return w_int.intval
        else:
            # XXX argh.  should attempt conversion
            raise OperationError(
                self.space.w_TypeError,
                self.space.W_StringObject("an integer is required"))
    def get_max(self):
        import sys
        return self.from_long(sys.maxint)
    
class FloatObjSpace(ConcreteSpace):
    __slots__ = []
    def check(self, ob):
        return isinstance(ob, self.space.W_FloatObject)
    def check_exact(self, ob):
        return ob.__class__ is self.space.W_FloatObject
    def from_string(self, w_str):
        return self.from_double(float(w_str))
    def from_double(self, d):
        return self.space.W_FloatObject(d)
    def as_double(self, w_float):
        if self.check(w_float):
            return w_float.floatval
        else:
            # XXX argh.  should attempt conversion
            raise OperationError(
                self.space.w_TypeError,
                self.space.W_StringObject("a float is required"))
    
