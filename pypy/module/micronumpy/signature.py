from pypy.rlib.objectmodel import r_dict, compute_identity_hash
from pypy.module.micronumpy.interp_iter import ViewIterator, ArrayIterator, \
     BroadcastIterator, OneDimIterator, ConstantIterator
from pypy.rlib.jit import hint, unroll_safe

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
    try:
        return known_sigs[sig]
    except KeyError:
        sig.invent_numbering()
        known_sigs[sig] = sig
        return sig

class NumpyEvalFrame(object):
    _virtualizable2_ = ['iterators[*]']

    def __init__(self, iterators):
        self = hint(self, access_directly=True)
        self.iterators = iterators
        self.final_iter = None
        for i, iter in enumerate(self.iterators):
            if not isinstance(iter, ConstantIterator) or not isinstance(iter, BroadcastIterator):
                self.final_iter = i
                break
        else:
            raise Exception("Cannot find a non-broadcast non-constant iter")

    def done(self):
        return self.iterators[self.final_iter].done()

    @unroll_safe
    def next(self, shapelen):
        for i in range(len(self.iterators)):
            self.iterators[i] = self.iterators[i].next(shapelen)

class Signature(object):
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

    def create_frame(self, arr, res_shape=None):
        iterlist = []
        self._create_iter(iterlist, arr, res_shape)
        return NumpyEvalFrame(iterlist)

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

    def _create_iter(self, iterlist, arr, res_shape):
        if self.iter_no >= len(iterlist):
            iter = ArrayIterator(arr.size)
            iterlist.append(iter)

    def eval(self, frame, arr):
        iter = frame.iterators[self.iter_no]
        return arr.dtype.getitem(arr.storage, iter.offset)

class ScalarSignature(ConcreteSignature):
    def debug_repr(self):
        return 'Scalar'

    def _create_iter(self, iterlist, arr, res_shape):
        if self.iter_no >= len(iterlist):
            iter = ConstantIterator()
            iterlist.append(iter)

    def eval(self, frame, arr):
        return arr.value

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

    def _create_iter(self, iterlist, arr, res_shape):
        if self.iter_no >= len(iterlist):
            iter = ViewIterator(arr)
            iterlist.append(iter)

class FlatiterSignature(ViewSignature):
    def debug_repr(self):
        return 'FlatIter(%s)' % self.child.debug_repr()

    def _create_iter(self, iterlist, arr, res_shape):
        XXX

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

    def _create_iter(self, iterlist, arr, res_shape):
        self.child._create_iter(iterlist, arr.values, res_shape)

    def eval(self, frame, arr):
        v = self.child.eval(frame, arr.values).convert_to(arr.res_dtype)
        return self.unfunc(arr.res_dtype, v)

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

    def _create_iter(self, iterlist, arr, res_shape):
        self.left._create_iter(iterlist, arr.left, res_shape)
        self.right._create_iter(iterlist, arr.right, res_shape)

    def eval(self, frame, arr):
        lhs = self.left.eval(frame, arr.left).convert_to(arr.calc_dtype)
        rhs = self.right.eval(frame, arr.right).convert_to(arr.calc_dtype)
        return self.binfunc(arr.calc_dtype, lhs, rhs)

    def debug_repr(self):
        return 'Call2(%s, %s, %s)' % (self.name,
                                      self.left.debug_repr(),
                                      self.right.debug_repr())

class ReduceSignature(Call2):
    def _create_iter(self, iterlist, arr, res_shape):
        self.right._create_iter(iterlist, arr, res_shape)

    def _invent_numbering(self, cache):
        self.right._invent_numbering(cache)

    def eval(self, frame, arr):
        return self.right.eval(frame, arr)
