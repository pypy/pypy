from pypy.objspace.std.objspace import *
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.stringobject import W_StringObject

from pypy.objspace.std import slicetype
from pypy.interpreter import gateway, baseobjspace
from pypy.rlib.listsort import TimSort


class ListImplementation(object):

    def __init__(self, space):
        self.space = space

# A list implementation should implement the following methods:

##     def length(self):
##         pass

##     def getitem(self, i):
##         pass

##     def getitem_slice(self, start, stop):
##         pass


# the following operations return the list implementation that should
# be used after the call
# If it turns out that the list implementation cannot really perform
# the operation it can return None for the following ones:

    def setitem(self, i, w_item):
        pass

    def insert(self, i, w_item):
        pass

    def delitem(self, index):
        pass

    def delitem_slice(self, start, stop):
        pass

    def append(self, w_item):
        pass

    def extend(self, other):
        pass


# special cases:

    def add(self, other):
        pass

##     def get_list_w(self):
##         pass

# default implementations, can (but don't have to be) overridden:

    def reverse(self):
        l = self.length()
        for i in range(l // 2):
            x = self.getitem(i)
            y = self.getitem(l - i - 1)
            self = self.i_setitem(i, y)
            self = self.i_setitem(l - i - 1, x)
        return self


    def getitem_slice_step(self, start, stop, step, slicelength):
        res_w = [None] * slicelength
        for i in range(slicelength):
            res_w[i] = self.getitem(start)
            start += step
        return RListImplementation(self.space, res_w)

    def delitem_slice_step(self, start, stop, step, slicelength):
        n = self.length()

        recycle = [None] * slicelength
        i = start

        # keep a reference to the objects to be removed,
        # preventing side effects during destruction
        recycle[0] = self.getitem(i)

        for discard in range(1, slicelength):
            j = i+1
            i += step
            while j < i:
                self = self.i_setitem(j - discard, self.getitem(j))
                j += 1
            recycle[discard] = self.getitem(i)

        j = i+1
        while j < n:
            self = self.i_setitem(j-slicelength, self.getitem(j))
            j += 1
        start = n - slicelength
        assert start >= 0 # annotator hint
        self = self.i_delitem_slice(start, n)
        return self
   
    def mul(self, times):
        return make_implementation(self.space, self.get_list_w() * times)

    def copy(self):
        return self.getitem_slice(0, self.length())

    def to_rlist(self):
        list_w = self.get_list_w()
        return RListImplementation(self.space, list_w)

    # interface used by W_ListMultiObject:

    def i_setitem(self, i, w_item):
        impl = self.setitem(i, w_item)
        if impl is None: # failed to implement
            list_w = self.get_list_w()
            assert i >= 0 and i < len(list_w)
            list_w[i] = w_item
            return self.make_implementation(list_w)
        return impl

    def i_insert(self, i, w_item):
        impl = self.insert(i, w_item)
        if impl is None: # failed to implement
            list_w = self.get_list_w()
            assert i >= 0 and i <= len(list_w)
            list_w.insert(i, w_item)
            return self.make_implementation(list_w)
        return impl

    def i_append(self, w_item):
        impl = self.append(w_item)
        if impl is None: # failed to implement
            list_w = self.get_list_w()
            list_w.append(w_item)
            return self.make_implementation(list_w)
        return impl

    def i_add(self, other):
        impl = self.add(other)
        if impl is None:
            list_w1 = self.get_list_w()
            list_w2 = other.get_list_w()
            return self.make_implementation(list_w1 + list_w2)
        return impl

    def i_extend(self, other):
        impl = self.extend(other)
        if impl is None:
            list_w1 = self.get_list_w()
            list_w2 = other.get_list_w()
            return self.make_implementation(list_w1 + list_w2)
        return impl

    def i_delitem(self, i):
        impl = self.delitem(i)
        if impl is None:
            list_w = self.get_list_w()
            del list_w[i]
            return self.make_implementation(list_w)
        return impl

    def i_delitem_slice(self, start, stop):
        impl = self.delitem_slice(start, stop)
        if impl is None:
            list_w = self.get_list_w()
            assert 0 <= start < len(list_w)
            assert 0 <= stop <= len(list_w)
            del list_w[start:stop]
            return self.make_implementation(list_w)
        return impl

    def make_implementation(self, list_w):
        space = self.space
        if space.config.objspace.std.withsmartresizablelist:
            from pypy.objspace.std.smartresizablelist import \
                SmartResizableListImplementation
            impl = SmartResizableListImplementation(space)
            impl.extend(RListImplementation(space, list_w))
            return impl
        if space.config.objspace.std.withfastslice:
            return SliceTrackingListImplementation(space, list_w)
        else:
            return RListImplementation(space, list_w)


class RListImplementation(ListImplementation):
    def __init__(self, space, list_w):
        ListImplementation.__init__(self, space)
        self.list_w = list_w

    def length(self):
        return len(self.list_w)

    def getitem(self, i):
        return self.list_w[i]

    def getitem_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0 and stop <= len(self.list_w)
        return RListImplementation(self.space, self.list_w[start:stop])

    def delitem(self, i):
        assert i >= 0 and i < len(self.list_w)
        if len(self.list_w) == 1:
            return self.space.fromcache(State).empty_impl
        del self.list_w[i]
        return self

    def delitem_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0 and stop <= len(self.list_w)
        if len(self.list_w) == stop and start == 0:
            return self.space.fromcache(State).empty_impl
        del self.list_w[start:stop]
        return self
    
    def setitem(self, i, w_item):
        assert i >= 0 and i < len(self.list_w)
        self.list_w[i] = w_item
        return self

    def insert(self, i, w_item):
        assert i >= 0 and i <= len(self.list_w)
        self.list_w.insert(i, w_item)
        return self

    def add(self, other):
        return RListImplementation(
            self.space, self.list_w + other.get_list_w())

    def append(self, w_item):
        self.list_w.append(w_item)
        return self

    def extend(self, other):
        self.list_w.extend(other.get_list_w())
        return self

    def reverse(self):
        self.list_w.reverse()
        return self

    def get_list_w(self):
        return self.list_w

    def to_rlist(self):
        return self
    
    def __repr__(self):
        return "RListImplementation(%s)" % (self.list_w, )

class EmptyListImplementation(ListImplementation):
    def make_list_with_one_item(self, w_item):
        space = self.space
        if space.config.objspace.std.withfastslice:
            return SliceTrackingListImplementation(space, [w_item])
        w_type = space.type(w_item)
        if space.is_w(w_type, space.w_str):
            strlist = [space.str_w(w_item)]
            return StrListImplementation(space, strlist)
        return RListImplementation(space, [w_item])

    def length(self):
        return 0

    def getitem(self, i):
        raise IndexError

    def getitem_slice(self, start, stop):
        if start == 0 and stop == 0:
            return self
        raise IndexError

    def delitem(self, index):
        raise IndexError

    def delitem_slice(self, start, stop):
        if start == 0 and stop == 0:
            return self
        raise IndexError

    def setitem(self, i, w_item):
        raise IndexError

    def insert(self, i, w_item):
        return self.make_list_with_one_item(w_item)

    def add(self, other):
        return other.copy()

    def append(self, w_item):
        return self.make_list_with_one_item(w_item)

    def extend(self, other):
        return other.copy()

    def reverse(self):
        return self

    def get_list_w(self):
        return []

    def copy(self):
        return self

    def mul(self, times):
        return self

    def __repr__(self):
        return "EmptyListImplementation()"

class StrListImplementation(ListImplementation):
    def __init__(self, space, strlist):
        self.strlist = strlist
        ListImplementation.__init__(self, space)

    def length(self):
        return len(self.strlist)

    def getitem(self, i):
        assert 0 <= i < len(self.strlist)
        return self.space.wrap(self.strlist[i])

    def getitem_slice(self, start, stop):
        assert 0 <= start < len(self.strlist)
        assert 0 <= stop <= len(self.strlist)
        return StrListImplementation(self.space, self.strlist[start:stop])

    def getitem_slice_step(self, start, stop, step, slicelength):
        assert 0 <= start < len(self.strlist)
        assert 0 <= stop < len(self.strlist)
        assert slicelength > 0
        res = [0] * slicelength
        for i in range(slicelength):
            res[i] = self.strlist[start]
            start += step
        return StrListImplementation(self.space, res)

    def delitem(self, i):
        assert 0 <= i < len(self.strlist)
        if len(self.strlist) == 1:
            return self.space.fromcache(State).empty_impl
        del self.strlist[i]
        return self

    def delitem_slice(self, start, stop):
        assert 0 <= start < len(self.strlist)
        assert 0 <= stop < len(self.strlist)
        if len(self.strlist) == stop and start == 0:
            return self.space.fromcache(State).empty_impl
        del self.strlist[start:stop]
        return self
    
    def setitem(self, i, w_item):
        assert 0 <= i < len(self.strlist)
        if self.space.is_w(self.space.type(w_item), self.space.w_str):
            self.strlist[i] = self.space.str_w(w_item)
            return self
        return None
        
    def insert(self, i, w_item):
        assert 0 <= i <= len(self.strlist)
        if self.space.is_w(self.space.type(w_item), self.space.w_str):
            self.strlist.insert(i, self.space.str_w(w_item))
            return self
        return None

    def add(self, other):
        if isinstance(other, StrListImplementation):
            return StrListImplementation(
                self.space, self.strlist + other.strlist)

    def append(self, w_item):
        if self.space.is_w(self.space.type(w_item), self.space.w_str):
            self.strlist.append(self.space.str_w(w_item))
            return self
        return None

    def extend(self, other):
        if isinstance(other, StrListImplementation):
            self.strlist.extend(other.strlist)
            return self

    def reverse(self):
        self.strlist.reverse()
        return self

    def get_list_w(self):
        return [self.space.wrap(i) for i in self.strlist]

    def __repr__(self):
        return "StrListImplementation(%s)" % (self.strlist, )


class RangeImplementation(ListImplementation):
    def __init__(self, space, start, step, length):
        ListImplementation.__init__(self, space)
        self.start = start
        self.step = step
        self.len = length

    def length(self):
        return self.len

    def getitem_w(self, i):
        assert 0 <= i < self.len
        return self.start + i * self.step

    def getitem(self, i):
        return wrapint(self.space, self.getitem_w(i))

    def getitem_slice(self, start, stop):
        rangestart = self.getitem_w(start)
        return RangeImplementation(
            self.space, rangestart, self.step, stop - start)

    def getitem_slice_step(self, start, stop, step, slicelength):
        rangestart = self.getitem_w(start)
        rangestep = self.step * step
        return RangeImplementation(
            self.space, rangestart, rangestep, slicelength)

    def delitem(self, index):
        if index == 0:
            self.start = self.getitem_w(1)
            self.len -= 1
            return self
        if index == self.len - 1:
            self.len -= 1
            return self
        return None

    def delitem_slice(self, start, stop):
        if start == 0:
            if stop == self.len:
                return self.space.fromcache(State).empty_impl
            self.start = self.getitem_w(stop)
            self.len -= stop
            return self
        if stop == self.len:
            self.len = start
            return self
        return None
    
    def reverse(self):
        self.start = self.getitem_w(self.len - 1)
        self.step = -self.step
        return self

    def get_list_w(self):
        start = self.start
        step = self.step
        length = self.len
        if not length:
            return []
        
        list_w = [None] * length

        i = start
        n = 0
        while n < length:
            list_w[n] = wrapint(self.space, i)
            i += step
            n += 1

        return list_w
 
    def __repr__(self):
        return "RangeImplementation(%s, %s, %s)" % (
            self.start, self.len, self.step)


class SliceTrackingListImplementation(RListImplementation):
    def __init__(self, space, list_w):
        RListImplementation.__init__(self, space, list_w)
        self.slices = []

    def getitem_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0 and stop <= len(self.list_w)
        # just do this for slices of a certain length
        if stop - start > 5:
            index = len(self.slices)
            sliceimpl = SliceListImplementation(
                    self.space, self, index, start, stop)
            self.slices.append(sliceimpl)
            return sliceimpl
        else:
            return self.getitem_true_slice(start, stop)

    def getitem_true_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0 and stop <= len(self.list_w)
        return SliceTrackingListImplementation(
                self.space, self.list_w[start:stop])

    def getitem_slice_step(self, start, stop, step, slicelength):
        res_w = [None] * slicelength
        for i in range(slicelength):
            res_w[i] = self.getitem(start)
            start += step
        return SliceTrackingListImplementation(self.space, res_w)

    def delitem(self, index):
        assert 0 <= index < len(self.list_w)
        if len(self.list_w) == 1:
            return self.space.fromcache(State).empty_impl
        self.changed()
        del self.list_w[index]
        return self

    def delitem_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0 and stop <= len(self.list_w)
        if start == 0 and len(self.list_w) == stop:
            return self.space.fromcache(State).empty_impl
        self.changed()
        del self.list_w[start:stop]
        return self
    
    def setitem(self, i, w_item):
        self.changed()
        assert 0 <= i < len(self.list_w)
        self.list_w[i] = w_item
        return self

    def insert(self, i, w_item):
        assert 0 <= i <= len(self.list_w)
        if i == len(self.list_w):
            return self.append(w_item)
        self.changed()
        self.list_w.insert(i, w_item)
        return self

    def add(self, other):
        if isinstance(other, SliceTrackingListImplementation):
            return SliceTrackingListImplementation(
                self.space, self.list_w + other.list_w)
        return SliceTrackingListImplementation(
            self.space, self.list_w + other.get_list_w())

    # append and extend need not be overridden from RListImplementation.__init__
    # they change the list but cannot affect slices taken so far

    def reverse(self):
        # could be optimised: the slices grow steps and their
        # step is reversed :-)
        self.changed()
        self.list_w.reverse()
        return self

    def to_rlist(self):
        return RListImplementation(self.space, self.list_w)

    def changed(self):
        if not self.slices:
            return
        self.notify_slices()
    
    def notify_slices(self):
        for slice in self.slices:
            if slice is not None:
                slice.detach()
        self.slices = []

    def unregister_slice(self, index):
        self.slices[index] = None

    def __repr__(self):
        return "SliceTrackingListImplementation(%s, <%s slice(s)>)" % (
            self.list_w, len(self.slices))

class SliceListImplementation(ListImplementation):
    def __init__(self, space, listimpl, index, start, stop):
        assert 0 <= start < listimpl.length()
        assert 0 <= stop <= listimpl.length()
        ListImplementation.__init__(self, space)
        self.listimpl = listimpl
        self.index = index
        self.start = start
        self.stop = stop
        self.len = stop - start
        self.detached_impl = None

    def detach(self):
        if self.detached_impl is None:
            self.detached_impl = self.listimpl.getitem_true_slice(
                self.start, self.stop)
            self.listimpl = None # loose the reference

    def detach_and_unregister(self):
        if self.detached_impl is None:
            self.listimpl.unregister_slice(self.index)
            self.detach()

    def length(self):
        if self.detached_impl is not None:
            return self.detached_impl.length()
        return self.len

    def getitem(self, i):
        if self.detached_impl is not None:
            return self.detached_impl.getitem(i)
        return self.listimpl.getitem(self.start + i)

    def getitem_slice(self, start, stop):
        assert start >= 0
        assert stop >= 0
        if self.detached_impl is not None:
            return self.detached_impl.getitem_slice(start, stop)
        return self.listimpl.getitem_slice(
            self.start + start, self.start + stop)

    def delitem(self, index):
        self.detach_and_unregister()
        return self.detached_impl.delitem(index)

    def delitem_slice(self, start, stop):
        self.detach_and_unregister()
        if start == 0 and self.len == stop:
            return self.space.fromcache(State).empty_impl
        return self.detached_impl.delitem_slice(start, stop)
    
    def setitem(self, i, w_item):
        self.detach_and_unregister()
        return self.detached_impl.setitem(i, w_item)

    def insert(self, i, w_item):
        self.detach_and_unregister()
        return self.detached_impl.insert(i, w_item)

    def add(self, other):
        self.detach_and_unregister()
        return self.detached_impl.add(other)

    def append(self, w_item):
        self.detach_and_unregister()
        return self.detached_impl.append(w_item)

    def extend(self, other):
        self.detach_and_unregister()
        return self.detached_impl.extend(other)

    def reverse(self):
        self.detach_and_unregister()
        return self.detached_impl.reverse()

    def get_list_w(self):
        self.detach_and_unregister()
        return self.detached_impl.get_list_w()

    def __repr__(self):
        if self.detached_impl is not None:
            return "SliceListImplementation(%s)" % (self.detached_impl, )
        return "SliceListImplementation(%s, %s, %s)" % (
            self.listimpl, self.start, self.stop)



def is_homogeneous(space, list_w, w_type):
    for i in range(len(list_w)):
        if not space.is_w(w_type, space.type(list_w[i])):
            return False
    return True

def make_implementation(space, list_w):
    if list_w:
        if space.config.objspace.std.withsmartresizablelist:
            from pypy.objspace.std.smartresizablelist import \
                SmartResizableListImplementation
            impl = SmartResizableListImplementation(space)
            impl.extend(RListImplementation(space, list_w))
            return impl
        if space.config.objspace.std.withfastslice:
            impl = SliceTrackingListImplementation(space, list_w)
        else:
            w_type = space.type(list_w[0])
            if (space.is_w(w_type, space.w_str) and
                is_homogeneous(space, list_w, w_type)):
                strlist = [space.str_w(w_i) for w_i in list_w]
                impl = StrListImplementation(space, strlist)
            else:
                impl = RListImplementation(space, list_w)
    else:
        impl = space.fromcache(State).empty_impl
    return impl

def convert_list_w(space, list_w):
    impl = make_implementation(space, list_w)
    return W_ListMultiObject(space, impl)


class W_ListMultiObject(W_Object):
    from pypy.objspace.std.listtype import list_typedef as typedef
    
    def __init__(w_self, space, implementation=None):
        if implementation is None:
            implementation = space.fromcache(State).empty_impl
        w_self.implementation = implementation

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.implementation)

    def unwrap(w_list, space):
        items = [space.unwrap(w_item)
                    for w_item in w_list.implementation.get_list_w()]
        return items

registerimplementation(W_ListMultiObject)

class State(object):
    def __init__(self, space):
        self.empty_impl = EmptyListImplementation(space)
        self.empty_list = W_ListMultiObject(space, self.empty_impl)


def _adjust_index(space, index, length, indexerrormsg):
    if index < 0:
        index += length
    if index < 0 or index >= length:
        raise OperationError(space.w_IndexError,
                             space.wrap(indexerrormsg))
    return index


def init__ListMulti(space, w_list, __args__):
    EMPTY_LIST = space.fromcache(State).empty_list
    w_iterable, = __args__.parse('list',
                               (['sequence'], None, None),   # signature
                               [EMPTY_LIST])                 # default argument
    if w_iterable is not EMPTY_LIST:
        list_w = space.unpackiterable(w_iterable)
        if list_w:
            w_list.implementation = RListImplementation(space, list_w)
            return
    w_list.implementation = space.fromcache(State).empty_impl

def len__ListMulti(space, w_list):
    result = w_list.implementation.length()
    return wrapint(space, result)

def getitem__ListMulti_ANY(space, w_list, w_index):
    idx = space.int_w(w_index)
    idx = _adjust_index(space, idx, w_list.implementation.length(),
                        "list index out of range")
    return w_list.implementation.getitem(idx)

def getitem__ListMulti_Slice(space, w_list, w_slice):
    length = w_list.implementation.length()
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    if step == 1 and 0 <= start <= stop:
        return W_ListMultiObject(
            space,
            w_list.implementation.getitem_slice(start, stop))
    return W_ListMultiObject(
        space,
        w_list.implementation.getitem_slice_step(
            start, stop, step, slicelength))

def contains__ListMulti_ANY(space, w_list, w_obj):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    impl = w_list.implementation
    while i < impl.length(): # intentionally always calling len!
        if space.eq_w(impl.getitem(i), w_obj):
            return space.w_True
        i += 1
    return space.w_False

def iter__ListMulti(space, w_list):
    from pypy.objspace.std import iterobject
    return iterobject.W_SeqIterObject(w_list)

def add__ListMulti_ListMulti(space, w_list1, w_list2):
    impl = w_list1.implementation.i_add(w_list2.implementation)
    return W_ListMultiObject(space, impl)

def inplace_add__ListMulti_ANY(space, w_list1, w_iterable2):
    list_extend__ListMulti_ANY(space, w_list1, w_iterable2)
    return w_list1

def inplace_add__ListMulti_ListMulti(space, w_list1, w_list2):
    list_extend__ListMulti_ListMulti(space, w_list1, w_list2)
    return w_list1

def mul_list_times(space, w_list, w_times):
    try:
        times = space.int_w(w_times)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    return W_ListMultiObject(space, w_list.implementation.mul(times))

def mul__ListMulti_ANY(space, w_list, w_times):
    return mul_list_times(space, w_list, w_times)

def mul__ANY_ListMulti(space, w_times, w_list):
    return mul_list_times(space, w_list, w_times)

def inplace_mul__ListMulti_ANY(space, w_list, w_times):
    try:
        times = space.int_w(w_times)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    # XXX could be more efficient?
    w_list.implementation = w_list.implementation.mul(times)
    return w_list

def eq__ListMulti_ListMulti(space, w_list1, w_list2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    impl1 = w_list1.implementation
    impl2 = w_list2.implementation
    return equal_impls(space, impl1, impl2)

def equal_impls(space, impl1, impl2):
    if impl1.length() != impl2.length():
        return space.w_False
    i = 0
    while i < impl1.length() and i < impl2.length():
        if not space.eq_w(impl1.getitem(i), impl2.getitem(i)):
            return space.w_False
        i += 1
    return space.w_True

def _min(a, b):
    if a < b:
        return a
    return b

def lessthan_impls(space, impl1, impl2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < impl1.length() and i < impl2.length():
        w_item1 = impl1.getitem(i)
        w_item2 = impl2.getitem(i)
        if not space.eq_w(w_item1, w_item2):
            return space.lt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(impl1.length() < impl2.length())

def greaterthan_impls(space, impl1, impl2):
    # needs to be safe against eq_w() mutating the w_lists behind our back
    # Search for the first index where items are different
    i = 0
    while i < impl1.length() and i < impl2.length():
        w_item1 = impl1.getitem(i)
        w_item2 = impl2.getitem(i)
        if not space.eq_w(w_item1, w_item2):
            return space.gt(w_item1, w_item2)
        i += 1
    # No more items to compare -- compare sizes
    return space.newbool(impl1.length() > impl2.length())

def lt__ListMulti_ListMulti(space, w_list1, w_list2):
    return lessthan_impls(space, w_list1.implementation,
        w_list2.implementation)

def gt__ListMulti_ListMulti(space, w_list1, w_list2):
    return greaterthan_impls(space, w_list1.implementation,
        w_list2.implementation)

def delitem__ListMulti_ANY(space, w_list, w_idx):
    idx = space.int_w(w_idx)
    length = w_list.implementation.length()
    idx = _adjust_index(space, idx, length, "list deletion index out of range")
    w_list.implementation = w_list.implementation.i_delitem(idx)
    return space.w_None

def delitem__ListMulti_Slice(space, w_list, w_slice):
    start, stop, step, slicelength = w_slice.indices4(
        space, w_list.implementation.length())

    if slicelength==0:
        return

    if step < 0:
        start = start + step * (slicelength-1)
        step = -step
        # stop is invalid
        
    if step == 1:
        _del_slice(w_list, start, start+slicelength)
    else:
        w_list.implementation = w_list.implementation.delitem_slice_step(
            start, start + slicelength, step, slicelength)

    return space.w_None

def setitem__ListMulti_ANY_ANY(space, w_list, w_index, w_any):
    idx = space.int_w(w_index)
    idx = _adjust_index(space, idx, w_list.implementation.length(),
                        "list index out of range")
    w_list.implementation = w_list.implementation.i_setitem(idx, w_any)
    return space.w_None

def setitem__ListMulti_Slice_ListMulti(space, w_list, w_slice, w_list2):
    impl = w_list2.implementation
    return _setitem_slice_helper(space, w_list, w_slice, impl)

def setitem__ListMulti_Slice_ANY(space, w_list, w_slice, w_iterable):
    l = RListImplementation(space, space.unpackiterable(w_iterable))
    return _setitem_slice_helper(space, w_list, w_slice, l)

def _setitem_slice_helper(space, w_list, w_slice, impl2):
    impl = w_list.implementation
    oldsize = impl.length()
    len2 = impl2.length()
    start, stop, step, slicelength = w_slice.indices4(space, oldsize)
    assert slicelength >= 0

    if step == 1:  # Support list resizing for non-extended slices
        delta = len2 - slicelength
        if delta >= 0:
            newsize = oldsize + delta
            impl = impl.i_extend(
                RListImplementation(space, [space.w_None] * delta))
            lim = start + len2
            i = newsize - 1
            while i >= lim:
                impl = impl.i_setitem(i, impl.getitem(i-delta))
                i -= 1
        else:
            # shrinking requires the careful memory management of _del_slice()
            impl = _del_slice(w_list, start, start-delta)
    elif len2 != slicelength:  # No resize for extended slices
        raise OperationError(space.w_ValueError, space.wrap("attempt to "
              "assign sequence of size %d to extended slice of size %d" %
              (len2,slicelength)))

    if impl2 is impl:
        if step > 0:
            # Always copy starting from the right to avoid
            # having to make a shallow copy in the case where
            # the source and destination lists are the same list.
            i = len2 - 1
            start += i*step
            while i >= 0:
                impl = impl.i_setitem(start, impl2.getitem(i))
                start -= step
                i -= 1
            return space.w_None
        else:
            # Make a shallow copy to more easily handle the reversal case
            impl2 = impl2.getitem_slice(0, impl2.length())
    for i in range(len2):
        impl = impl.i_setitem(start, impl2.getitem(i))
        start += step
    w_list.implementation = impl
    return space.w_None

app = gateway.applevel("""
    def listrepr(currently_in_repr, l):
        'The app-level part of repr().'
        list_id = id(l)
        if list_id in currently_in_repr:
            return '[...]'
        currently_in_repr[list_id] = 1
        try:
            return "[" + ", ".join([repr(x) for x in l]) + ']'
        finally:
            try:
                del currently_in_repr[list_id]
            except:
                pass
""", filename=__file__) 

listrepr = app.interphook("listrepr")

def repr__ListMulti(space, w_list):
    if w_list.implementation.length() == 0:
        return space.wrap('[]')
    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return listrepr(space, w_currently_in_repr, w_list)

def list_insert__ListMulti_ANY_ANY(space, w_list, w_where, w_any):
    where = space.int_w(w_where)
    length = w_list.implementation.length()
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    w_list.implementation = w_list.implementation.i_insert(where, w_any)
    return space.w_None

def list_append__ListMulti_ANY(space, w_list, w_any):
    w_list.implementation = w_list.implementation.i_append(w_any)
    return space.w_None

def list_extend__ListMulti_ListMulti(space, w_list, w_list2):
    impl2 = w_list2.implementation
    w_list.implementation = w_list.implementation.i_extend(impl2)
    return space.w_None

def list_extend__ListMulti_ANY(space, w_list, w_any):
    list_w2 = space.unpackiterable(w_any)
    impl2 = RListImplementation(space, list_w2)
    w_list.implementation = w_list.implementation.i_extend(impl2)
    return space.w_None

def _del_slice(w_list, ilow, ihigh):
    """ similar to the deletion part of list_ass_slice in CPython """
    impl = w_list.implementation
    n = impl.length()
    if ilow < 0:
        ilow = 0
    elif ilow > n:
        ilow = n
    if ihigh < ilow:
        ihigh = ilow
    elif ihigh > n:
        ihigh = n
    # keep a reference to the objects to be removed,
    # preventing side effects during destruction
    recycle = impl.getitem_slice(ilow, ihigh)
    newimpl = w_list.implementation = impl.i_delitem_slice(ilow, ihigh)
    return newimpl


def list_pop__ListMulti_ANY(space, w_list, w_idx=-1):
    impl = w_list.implementation
    length = impl.length()
    if length == 0:
        raise OperationError(space.w_IndexError,
                             space.wrap("pop from empty list"))
    idx = space.int_w(w_idx)
    idx = _adjust_index(space, idx, length, "pop index out of range")
    w_result = impl.getitem(idx)
    w_list.implementation = impl.i_delitem(idx)
    return w_result

def list_remove__ListMulti_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    i = 0
    while i < w_list.implementation.length():
        if space.eq_w(w_list.implementation.getitem(i), w_any):
            if i < w_list.implementation.length():
                w_list.implementation = w_list.implementation.i_delitem(i)
            return space.w_None
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.remove(x): x not in list"))

def list_index__ListMulti_ANY_ANY_ANY(space, w_list, w_any, w_start, w_stop):
    # needs to be safe against eq_w() mutating the w_list behind our back
    length = w_list.implementation.length()
    w_start = slicetype.adapt_bound(space, w_start, space.wrap(length))
    w_stop = slicetype.adapt_bound(space, w_stop, space.wrap(length))
    i = space.int_w(w_start)
    stop = space.int_w(w_stop)
    while i < stop and i < w_list.implementation.length():
        if space.eq_w(w_list.implementation.getitem(i), w_any):
            return space.wrap(i)
        i += 1
    raise OperationError(space.w_ValueError,
                         space.wrap("list.index(x): x not in list"))

def list_count__ListMulti_ANY(space, w_list, w_any):
    # needs to be safe against eq_w() mutating the w_list behind our back
    count = 0
    i = 0
    while i < w_list.implementation.length():
        if space.eq_w(w_list.implementation.getitem(i), w_any):
            count += 1
        i += 1
    return space.wrap(count)

def list_reverse__ListMulti(space, w_list):
    w_list.implementation = w_list.implementation.reverse()
    return space.w_None

# ____________________________________________________________
# Sorting

# Reverse a slice of a list in place, from lo up to (exclusive) hi.
# (used in sort)

class KeyContainer(baseobjspace.W_Root):
    def __init__(self, w_key, w_item):
        self.w_key = w_key
        self.w_item = w_item

# NOTE: all the subclasses of TimSort should inherit from a common subclass,
#       so make sure that only SimpleSort inherits directly from TimSort.
#       This is necessary to hide the parent method TimSort.lt() from the
#       annotator.
class SimpleSort(TimSort):
    def lt(self, a, b):
        space = self.space
        return space.is_true(space.lt(a, b))

class CustomCompareSort(SimpleSort):
    def lt(self, a, b):
        space = self.space
        w_cmp = self.w_cmp
        w_result = space.call_function(w_cmp, a, b)
        try:
            result = space.int_w(w_result)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                raise OperationError(space.w_TypeError,
                    space.wrap("comparison function must return int"))
            raise
        return result < 0

class CustomKeySort(SimpleSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        space = self.space
        return space.is_true(space.lt(a.w_key, b.w_key))

class CustomKeyCompareSort(CustomCompareSort):
    def lt(self, a, b):
        assert isinstance(a, KeyContainer)
        assert isinstance(b, KeyContainer)
        return CustomCompareSort.lt(self, a.w_key, b.w_key)

def list_sort__ListMulti_ANY_ANY_ANY(space, w_list, w_cmp, w_keyfunc, w_reverse):
    has_cmp = not space.is_w(w_cmp, space.w_None)
    has_key = not space.is_w(w_keyfunc, space.w_None)
    has_reverse = space.is_true(w_reverse)

    # create and setup a TimSort instance
    if has_cmp: 
        if has_key: 
            sorterclass = CustomKeyCompareSort
        else: 
            sorterclass = CustomCompareSort
    else: 
        if has_key: 
            sorterclass = CustomKeySort
        else: 
            sorterclass = SimpleSort
    impl = w_list.implementation.to_rlist()
    w_list.implementation = impl
    items = impl.list_w
    sorter = sorterclass(items, impl.length())
    sorter.space = space
    sorter.w_cmp = w_cmp

    try:
        # The list is temporarily made empty, so that mutations performed
        # by comparison functions can't affect the slice of memory we're
        # sorting (allowing mutations during sorting is an IndexError or
        # core-dump factory).
        w_list.implementation = EmptyListImplementation(space)

        # wrap each item in a KeyContainer if needed
        if has_key:
            for i in range(sorter.listlength):
                w_item = sorter.list[i]
                w_key = space.call_function(w_keyfunc, w_item)
                sorter.list[i] = KeyContainer(w_key, w_item)

        # Reverse sort stability achieved by initially reversing the list,
        # applying a stable forward sort, then reversing the final result.
        if has_reverse:
            sorter.list.reverse()

        # perform the sort
        sorter.sort()

        # reverse again
        if has_reverse:
            sorter.list.reverse()

    finally:
        # unwrap each item if needed
        if has_key:
            for i in range(sorter.listlength):
                w_obj = sorter.list[i]
                if isinstance(w_obj, KeyContainer):
                    sorter.list[i] = w_obj.w_item

        # check if the user mucked with the list during the sort
        mucked = w_list.implementation.length() > 0

        # put the items back into the list
        impl.list_w = sorter.list
        w_list.implementation = impl

    if mucked:
        raise OperationError(space.w_ValueError,
                             space.wrap("list modified during sort"))

    return space.w_None


from pypy.objspace.std import listtype
register_all(vars(), listtype)
