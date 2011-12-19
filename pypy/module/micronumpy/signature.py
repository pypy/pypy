from pypy.rlib.objectmodel import r_dict, compute_identity_hash, compute_hash
from pypy.rlib.rarithmetic import intmask
from pypy.module.micronumpy.interp_iter import ViewIterator, ArrayIterator, \
     OneDimIterator, ConstantIterator
from pypy.rpython.lltypesystem.llmemory import cast_ptr_to_adr
from pypy.rlib.jit import hint, unroll_safe, promote

def sigeq(one, two):
    return one.eq(two)

def sigeq2(one, two):
    return one.eq(two, compare_array_no=False)

def sighash(sig):
    return sig.hash()

known_sigs = r_dict(sigeq, sighash)

def find_sig(sig, arr):
    sig.invent_array_numbering(arr)
    try:
        return known_sigs[sig]
    except KeyError:
        sig.invent_numbering()
        known_sigs[sig] = sig
        return sig

class NumpyEvalFrame(object):
    _virtualizable2_ = ['iterators[*]', 'final_iter', 'arraylist[*]']

    @unroll_safe
    def __init__(self, iterators, arrays):
        self = hint(self, access_directly=True, fresh_virtualizable=True)
        self.iterators = iterators[:]
        self.arrays = arrays[:]
        for i in range(len(self.iterators)):
            iter = self.iterators[i]
            if not isinstance(iter, ConstantIterator):# or not isinstance(iter, BroadcastIterator):
                self.final_iter = i
                break
        else:
            self.final_iter = -1

    def done(self):
        final_iter = promote(self.final_iter)
        if final_iter < 0:
            return False
        return self.iterators[final_iter].done()

    @unroll_safe
    def next(self, shapelen):
        for i in range(len(self.iterators)):
            self.iterators[i] = self.iterators[i].next(shapelen)

def _add_ptr_to_cache(ptr, cache):
    i = 0
    for p in cache:
        if ptr == p:
            return i
        i += 1
    else:
        res = len(cache)
        cache.append(ptr)
        return res

class Signature(object):
    _attrs_ = ['iter_no', 'array_no']
    _immutable_fields_ = ['iter_no', 'array_no']

    array_no = 0
    iter_no = 0

    def invent_numbering(self):
        cache = r_dict(sigeq2, sighash)
        allnumbers = []
        self._invent_numbering(cache, allnumbers)

    def invent_array_numbering(self, arr):
        cache = []
        self._invent_array_numbering(arr, cache)

    def _invent_numbering(self, cache, allnumbers):
        try:
            no = cache[self]
        except KeyError:
            no = len(allnumbers)
            cache[self] = no
            allnumbers.append(no)
        self.iter_no = no

    def create_frame(self, arr):
        iterlist = []
        arraylist = []
        self._create_iter(iterlist, arraylist, arr)
        return NumpyEvalFrame(iterlist, arraylist)

class ConcreteSignature(Signature):
    _immutable_fields_ = ['dtype']

    def __init__(self, dtype):
        self.dtype = dtype

    def eq(self, other, compare_array_no=True):
        if type(self) is not type(other):
            return False
        assert isinstance(other, ConcreteSignature)
        if compare_array_no:
            if self.array_no != other.array_no:
                return False
        return self.dtype is other.dtype

    def hash(self):
        return compute_identity_hash(self.dtype)

class ArraySignature(ConcreteSignature):
    def debug_repr(self):
        return 'Array'

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import ConcreteArray
        assert isinstance(arr, ConcreteArray)
        self.array_no = _add_ptr_to_cache(arr.storage, cache)

    def _create_iter(self, iterlist, arraylist, arr):
        from pypy.module.micronumpy.interp_numarray import ConcreteArray
        assert isinstance(arr, ConcreteArray)
        if self.iter_no >= len(iterlist):
            iterlist.append(self.allocate_iter(arr))
        if self.array_no >= len(arraylist):
            arraylist.append(arr.storage)

    def allocate_iter(self, arr):
        return ArrayIterator(arr.size)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import ConcreteArray
        assert isinstance(arr, ConcreteArray)
        iter = frame.iterators[self.iter_no]
        return self.dtype.getitem(frame.arrays[self.array_no], iter.offset)

class ForcedSignature(ArraySignature):
    def debug_repr(self):
        return 'ForcedArray'

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import VirtualArray
        assert isinstance(arr, VirtualArray)
        arr = arr.forced_result
        self.array_no = _add_ptr_to_cache(arr.storage, cache)

    def _create_iter(self, iterlist, arraylist, arr):
        from pypy.module.micronumpy.interp_numarray import VirtualArray
        assert isinstance(arr, VirtualArray)
        arr = arr.forced_result
        if self.iter_no >= len(iterlist):
            iterlist.append(ArrayIterator(arr.size))
        if self.array_no >= len(arraylist):
            arraylist.append(arr.storage)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import VirtualArray
        assert isinstance(arr, VirtualArray)
        arr = arr.forced_result
        iter = frame.iterators[self.iter_no]
        return self.dtype.getitem(frame.arrays[self.array_no], iter.offset)    

class ScalarSignature(ConcreteSignature):
    def debug_repr(self):
        return 'Scalar'

    def _invent_array_numbering(self, arr, cache):
        pass

    def _create_iter(self, iterlist, arraylist, arr):
        if self.iter_no >= len(iterlist):
            iter = ConstantIterator()
            iterlist.append(iter)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Scalar
        assert isinstance(arr, Scalar)
        return arr.value

class ViewSignature(ArraySignature):
    def debug_repr(self):
        return 'Slice(%s)' % self.child.debug_repr()

    def _invent_numbering(self, cache, allnumbers):
        # always invent a new number for view
        no = len(allnumbers)
        allnumbers.append(no)
        self.iter_no = no

    def allocate_iter(self, arr):
        return ViewIterator(arr)

class FlatiterSignature(ViewSignature):
    def debug_repr(self):
        return 'FlatIter(%s)' % self.child.debug_repr()

    def _create_iter(self, iterlist, arraylist, arr):
        raise NotImplementedError

class Call1(Signature):
    _immutable_fields_ = ['unfunc', 'name', 'child']

    def __init__(self, func, name, child):
        self.unfunc = func
        self.child = child
        self.name = name

    def hash(self):
        return compute_hash(self.name) ^ intmask(self.child.hash() << 1)

    def eq(self, other, compare_array_no=True):
        if type(self) is not type(other):
            return False
        assert isinstance(other, Call1)
        return (self.unfunc is other.unfunc and
                self.child.eq(other.child, compare_array_no))

    def debug_repr(self):
        return 'Call1(%s, %s)' % (self.name, self.child.debug_repr())

    def _invent_numbering(self, cache, allnumbers):
        self.child._invent_numbering(cache, allnumbers)

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import Call1
        assert isinstance(arr, Call1)
        self.child._invent_array_numbering(arr.values, cache)

    def _create_iter(self, iterlist, arraylist, arr):
        from pypy.module.micronumpy.interp_numarray import Call1
        assert isinstance(arr, Call1)
        self.child._create_iter(iterlist, arraylist, arr.values)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Call1
        assert isinstance(arr, Call1)
        v = self.child.eval(frame, arr.values).convert_to(arr.res_dtype)
        return self.unfunc(arr.res_dtype, v)

class Call2(Signature):
    _immutable_fields_ = ['binfunc', 'name', 'calc_dtype', 'left', 'right']
    
    def __init__(self, func, name, calc_dtype, left, right):
        self.binfunc = func
        self.left = left
        self.right = right
        self.name = name
        self.calc_dtype = calc_dtype

    def hash(self):
        return (compute_hash(self.name) ^ intmask(self.left.hash() << 1) ^
                intmask(self.right.hash() << 2))

    def eq(self, other, compare_array_no=True):
        if type(self) is not type(other):
            return False
        assert isinstance(other, Call2)
        return (self.binfunc is other.binfunc and
                self.calc_dtype is other.calc_dtype and
                self.left.eq(other.left, compare_array_no) and
                self.right.eq(other.right, compare_array_no))

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import Call2
        assert isinstance(arr, Call2)
        self.left._invent_array_numbering(arr.left, cache)
        self.right._invent_array_numbering(arr.right, cache)

    def _invent_numbering(self, cache, allnumbers):
        self.left._invent_numbering(cache, allnumbers)
        self.right._invent_numbering(cache, allnumbers)

    def _create_iter(self, iterlist, arraylist, arr):
        from pypy.module.micronumpy.interp_numarray import Call2
        
        assert isinstance(arr, Call2)
        self.left._create_iter(iterlist, arraylist, arr.left)
        self.right._create_iter(iterlist, arraylist, arr.right)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Call2
        assert isinstance(arr, Call2)
        lhs = self.left.eval(frame, arr.left).convert_to(self.calc_dtype)
        rhs = self.right.eval(frame, arr.right).convert_to(self.calc_dtype)
        return self.binfunc(self.calc_dtype, lhs, rhs)

    def debug_repr(self):
        return 'Call2(%s, %s)' % (self.left.debug_repr(),
                                  self.right.debug_repr())

class ReduceSignature(Call2):
    def _create_iter(self, iterlist, arraylist, arr):
        self.right._create_iter(iterlist, arraylist, arr)

    def _invent_numbering(self, cache, allnumbers):
        self.right._invent_numbering(cache, allnumbers)

    def _invent_array_numbering(self, arr, cache):
        self.right._invent_array_numbering(arr, cache)

    def eval(self, frame, arr):
        return self.right.eval(frame, arr)
