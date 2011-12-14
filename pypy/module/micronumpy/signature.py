from pypy.rlib.objectmodel import r_dict, compute_identity_hash, compute_hash
from pypy.rlib.rarithmetic import intmask
from pypy.module.micronumpy.interp_iter import ViewIterator, ArrayIterator, \
     BroadcastIterator, OneDimIterator, ConstantIterator


# def components_eq(lhs, rhs):
#     if len(lhs) != len(rhs):
#         return False
#     for i in range(len(lhs)):
#         v1, v2 = lhs[i], rhs[i]
#         if type(v1) is not type(v2) or not v1.eq(v2):
#             return False
#     return True

# def components_hash(components):
#     res = 0x345678
#     for component in components:
#         res = intmask((1000003 * res) ^ component.hash())
#     return res

def sigeq(one, two):
    return one.eq(two)

def sighash(sig):
    return sig.hash()

known_sigs = r_dict(sigeq, sighash)

def find_sig(sig):
    return known_sigs.setdefault(sig, sig)

class Signature(object):
    def create_iter(self, array, cache, res_shape=None):
        raise NotImplementedError

    def invent_numbering(self):
        cache = r_dict(sigeq, sighash)
        self._invent_numbering(cache)

    def _invent_numbering(self, cache):
        try:
            no = cache[self]
        except KeyError:
            no = len(cache)
            cache[self] = no
        self.iter_no = no    

class ConcreteSignature(Signature):
    def __init__(self, dtype):
        self.dtype = dtype

    def eq(self, other):
        if type(self) is not type(other):
            return False
        return self.dtype is other.dtype

    def hash(self):
        return compute_identity_hash(self.dtype)

class ArraySignature(ConcreteSignature):
    def debug_repr(self):
        return 'Array'

class ScalarSignature(ConcreteSignature):
    def debug_repr(self):
        return 'Scalar'

class ViewSignature(Signature):
    def __init__(self, child):
        self.child = child
    
    def eq(self, other):
        if type(self) is not type(other):
            return False
        return self.child.eq(other.child)

    def hash(self):
        return self.child.hash() ^ 0x12345

    def debug_repr(self):
        return 'Slice(%s)' % self.child.debug_repr()

class FlatiterSignature(ViewSignature):
    def debug_repr(self):
        return 'FlatIter(%s)' % self.child.debug_repr()

class Call1(Signature):
    def __init__(self, func, child):
        self.unfunc = func
        self.child = child

    def hash(self):
        return compute_identity_hash(self.unfunc) ^ self.child.hash() << 1

    def eq(self, other):
        if type(self) is not type(other):
            return False
        return self.unfunc is other.unfunc and self.child.eq(other.child)

    def debug_repr(self):
        return 'Call1(%s, %s)' % (self.name,
                                  self.child.debug_repr())

    def _invent_numbering(self, cache):
        self.values._invent_numbering(cache)

class Call2(Signature):
    def __init__(self, func, left, right):
        self.binfunc = func
        self.left = left
        self.right = right

    def hash(self):
        return (compute_identity_hash(self.binfunc) ^ (self.left.hash() << 1) ^
                (self.right.hash() << 2))

    def eq(self, other):
        if type(self) is not type(other):
            return False
        return (self.binfunc is other.binfunc and
                self.left.eq(other.left) and self.right.eq(other.right))

    def _invent_numbering(self, cache):
        self.left._invent_numbering(cache)
        self.right._invent_numbering(cache)

    def debug_repr(self):
        return 'Call2(%s, %s, %s)' % (self.name,
                                      self.left.debug_repr(),
                                      self.right.debug_repr())

class ReduceSignature(Call2):
    pass
