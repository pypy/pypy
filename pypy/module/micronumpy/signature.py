from pypy.rlib.objectmodel import r_dict, compute_identity_hash, compute_hash
from pypy.rlib.rarithmetic import intmask
from pypy.module.micronumpy.interp_iter import ConstantIterator, AxisIterator,\
     ViewTransform, BroadcastTransform
from pypy.tool.pairtype import extendabletype
from pypy.module.micronumpy.loop import ComputationDone

""" Signature specifies both the numpy expression that has been constructed
and the assembler to be compiled. This is a very important observation -
Two expressions will be using the same assembler if and only if they are
compiled to the same signature.

This is also a very convinient tool for specializations. For example
a + a and a + b (where a != b) will compile to different assembler because
we specialize on the same array access.

When evaluating, signatures will create iterators per signature node,
potentially sharing some of them. Iterators depend also on the actual
expression, they're not only dependant on the array itself. For example
a + b where a is dim 2 and b is dim 1 would create a broadcasted iterator for
the array b.

Such iterator changes are called Transformations. An actual iterator would
be a combination of array and various transformation, like view, broadcast,
dimension swapping etc.

See interp_iter for transformations
"""

def new_printable_location(driver_name):
    def get_printable_location(shapelen, sig):
        return 'numpy ' + sig.debug_repr() + ' [%d dims,%s]' % (shapelen, driver_name)
    return get_printable_location

def sigeq(one, two):
    return one.eq(two)

def sigeq_no_numbering(one, two):
    """ Cache for iterator numbering should not compare array numbers
    """
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

def new_cache():
    return r_dict(sigeq_no_numbering, sighash)

class Signature(object):
    __metaclass_ = extendabletype
    
    _attrs_ = ['iter_no', 'array_no']
    _immutable_fields_ = ['iter_no', 'array_no']

    array_no = 0
    iter_no = 0

    def invent_numbering(self):
        cache = new_cache()
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
        from pypy.module.micronumpy.loop import NumpyEvalFrame
        
        iterlist = []
        arraylist = []
        self._create_iter(iterlist, arraylist, arr, [])
        f = NumpyEvalFrame(iterlist, arraylist)
        # hook for cur_value being used by reduce
        arr.compute_first_step(self, f)
        return f

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
        concr = arr.get_concrete()
        # this get_concrete never forces assembler. If we're here and array
        # is not of a concrete class it means that we have a _forced_result,
        # otherwise the signature would not match
        assert isinstance(concr, ConcreteArray)
        assert concr.dtype is self.dtype
        self.array_no = _add_ptr_to_cache(concr.storage, cache)

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import ConcreteArray
        concr = arr.get_concrete()
        assert isinstance(concr, ConcreteArray)
        storage = concr.storage
        if self.iter_no >= len(iterlist):
            iterlist.append(concr.create_iter(transforms))
        if self.array_no >= len(arraylist):
            arraylist.append(storage)

    def eval(self, frame, arr):
        iter = frame.iterators[self.iter_no]
        return self.dtype.getitem(frame.arrays[self.array_no], iter.offset)

class ScalarSignature(ConcreteSignature):
    def debug_repr(self):
        return 'Scalar'

    def _invent_array_numbering(self, arr, cache):
        pass

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        if self.iter_no >= len(iterlist):
            iter = ConstantIterator()
            iterlist.append(iter)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Scalar
        assert isinstance(arr, Scalar)
        return arr.value

class ViewSignature(ArraySignature):
    def debug_repr(self):
        return 'Slice'

    def _invent_numbering(self, cache, allnumbers):
        # always invent a new number for view
        no = len(allnumbers)
        allnumbers.append(no)
        self.iter_no = no

class FlatSignature(ViewSignature):
    def debug_repr(self):
        return 'Flat'

class VirtualSliceSignature(Signature):
    def __init__(self, child):
        self.child = child

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import VirtualSlice
        assert isinstance(arr, VirtualSlice)
        self.child._invent_array_numbering(arr.child, cache)

    def _invent_numbering(self, cache, allnumbers):
        self.child._invent_numbering(new_cache(), allnumbers)

    def hash(self):
        return intmask(self.child.hash() ^ 1234)

    def eq(self, other, compare_array_no=True):
        if type(self) is not type(other):
            return False
        assert isinstance(other, VirtualSliceSignature)
        return self.child.eq(other.child, compare_array_no)

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import VirtualSlice
        assert isinstance(arr, VirtualSlice)
        transforms = transforms + [ViewTransform(arr.chunks)]
        self.child._create_iter(iterlist, arraylist, arr.child, transforms)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import VirtualSlice
        assert isinstance(arr, VirtualSlice)
        return self.child.eval(frame, arr.child)

class Call1(Signature):
    _immutable_fields_ = ['unfunc', 'name', 'child', 'dtype']

    def __init__(self, func, name, dtype, child):
        self.unfunc = func
        self.child = child
        self.name = name
        self.dtype = dtype

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

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import Call1
        assert isinstance(arr, Call1)
        self.child._create_iter(iterlist, arraylist, arr.values, transforms)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Call1
        assert isinstance(arr, Call1)
        v = self.child.eval(frame, arr.values).convert_to(arr.calc_dtype)
        return self.unfunc(arr.calc_dtype, v)

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

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import Call2

        assert isinstance(arr, Call2)
        self.left._create_iter(iterlist, arraylist, arr.left, transforms)
        self.right._create_iter(iterlist, arraylist, arr.right, transforms)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Call2
        assert isinstance(arr, Call2)
        lhs = self.left.eval(frame, arr.left).convert_to(self.calc_dtype)
        rhs = self.right.eval(frame, arr.right).convert_to(self.calc_dtype)
        return self.binfunc(self.calc_dtype, lhs, rhs)

    def debug_repr(self):
        return 'Call2(%s, %s, %s)' % (self.name, self.left.debug_repr(),
                                      self.right.debug_repr())

class ResultSignature(Call2):
    def __init__(self, dtype, left, right):
        Call2.__init__(self, None, 'assign', dtype, left, right)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import ResultArray

        assert isinstance(arr, ResultArray)
        offset = frame.get_final_iter().offset
        arr.left.setitem(offset, self.right.eval(frame, arr.right))

class BroadcastLeft(Call2):
    def _invent_numbering(self, cache, allnumbers):
        self.left._invent_numbering(new_cache(), allnumbers)
        self.right._invent_numbering(cache, allnumbers)
    
    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import Call2

        assert isinstance(arr, Call2)
        ltransforms = transforms + [BroadcastTransform(arr.shape)]
        self.left._create_iter(iterlist, arraylist, arr.left, ltransforms)
        self.right._create_iter(iterlist, arraylist, arr.right, transforms)

class BroadcastRight(Call2):
    def _invent_numbering(self, cache, allnumbers):
        self.left._invent_numbering(cache, allnumbers)
        self.right._invent_numbering(new_cache(), allnumbers)

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import Call2

        assert isinstance(arr, Call2)
        rtransforms = transforms + [BroadcastTransform(arr.shape)]
        self.left._create_iter(iterlist, arraylist, arr.left, transforms)
        self.right._create_iter(iterlist, arraylist, arr.right, rtransforms)

class BroadcastBoth(Call2):
    def _invent_numbering(self, cache, allnumbers):
        self.left._invent_numbering(new_cache(), allnumbers)
        self.right._invent_numbering(new_cache(), allnumbers)

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import Call2

        assert isinstance(arr, Call2)
        rtransforms = transforms + [BroadcastTransform(arr.shape)]
        ltransforms = transforms + [BroadcastTransform(arr.shape)]
        self.left._create_iter(iterlist, arraylist, arr.left, ltransforms)
        self.right._create_iter(iterlist, arraylist, arr.right, rtransforms)

class ReduceSignature(Call2):
    _immutable_fields_ = ['binfunc', 'name', 'calc_dtype',
                          'left', 'right', 'done_func']
    
    def __init__(self, func, name, calc_dtype, left, right,
                 done_func):
        Call2.__init__(self, func, name, calc_dtype, left, right)
        self.done_func = done_func
        
    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import ReduceArray
        assert isinstance(arr, ReduceArray)
        rval = self.right.eval(frame, arr.right).convert_to(self.calc_dtype)
        if self.done_func is not None and self.done_func(self.calc_dtype, rval):
            raise ComputationDone(rval)
        frame.cur_value = self.binfunc(self.calc_dtype, frame.cur_value, rval)

    def debug_repr(self):
        return 'ReduceSig(%s)' % (self.name, self.right.debug_repr())

class SliceloopSignature(Call2):
    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import Call2
        
        assert isinstance(arr, Call2)
        ofs = frame.iterators[0].offset
        arr.left.setitem(ofs, self.right.eval(frame, arr.right).convert_to(
            self.calc_dtype))
    
    def debug_repr(self):
        return 'SliceLoop(%s, %s, %s)' % (self.name, self.left.debug_repr(),
                                          self.right.debug_repr())

class SliceloopBroadcastSignature(SliceloopSignature):
    def _invent_numbering(self, cache, allnumbers):
        self.left._invent_numbering(new_cache(), allnumbers)
        self.right._invent_numbering(cache, allnumbers)

    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import SliceArray

        assert isinstance(arr, SliceArray)
        rtransforms = transforms + [BroadcastTransform(arr.shape)]
        self.left._create_iter(iterlist, arraylist, arr.left, transforms)
        self.right._create_iter(iterlist, arraylist, arr.right, rtransforms)

class AxisReduceSignature(Call2):
    def _create_iter(self, iterlist, arraylist, arr, transforms):
        from pypy.module.micronumpy.interp_numarray import AxisReduce,\
             ConcreteArray

        assert isinstance(arr, AxisReduce)
        left = arr.left
        assert isinstance(left, ConcreteArray)
        iterlist.append(AxisIterator(left.start, arr.dim, arr.shape,
                                     left.strides, left.backstrides))
        self.right._create_iter(iterlist, arraylist, arr.right, transforms)

    def _invent_numbering(self, cache, allnumbers):
        allnumbers.append(0)
        self.right._invent_numbering(cache, allnumbers)

    def _invent_array_numbering(self, arr, cache):
        from pypy.module.micronumpy.interp_numarray import AxisReduce

        assert isinstance(arr, AxisReduce)
        self.right._invent_array_numbering(arr.right, cache)

    def eval(self, frame, arr):
        from pypy.module.micronumpy.interp_numarray import AxisReduce

        assert isinstance(arr, AxisReduce)
        iterator = frame.get_final_iter()
        v = self.right.eval(frame, arr.right).convert_to(self.calc_dtype)
        if iterator.first_line:
            if frame.identity is not None:
                value = self.binfunc(self.calc_dtype, frame.identity, v)
            else:
                value = v
        else:
            cur = arr.left.getitem(iterator.offset)
            value = self.binfunc(self.calc_dtype, cur, v)
        arr.left.setitem(iterator.offset, value)
    
    def debug_repr(self):
        return 'AxisReduceSig(%s, %s)' % (self.name, self.right.debug_repr())
