from pypy.rlib.objectmodel import r_dict
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation

# ____________________________________________________________
# Misc. utilities

def av_eq(self, other):
    return self.sort_key() == other.sort_key()

def av_hash(self):
    return self.sort_key()

def av_newdict():
    return r_dict(av_eq, av_hash)

def av_newdict2():
    # another implementation of av_newdict(), allowing different types for
    # the values...
    return r_dict(av_eq, av_hash)

def _findall(Class, name_prefix):
    result = []
    for value, name in resoperation.opname.items():
        if hasattr(Class, name_prefix + name):
            result.append((value, getattr(Class, name_prefix + name)))
    return unrolling_iterable(result)

def partition(array, left, right):
    last_item = array[right]
    pivot = last_item.sort_key()
    storeindex = left
    for i in range(left, right):
        if array[i].sort_key() <= pivot:
            array[i], array[storeindex] = array[storeindex], array[i]
            storeindex += 1
    # Move pivot to its final place
    array[storeindex], array[right] = last_item, array[storeindex]
    return storeindex

def quicksort(array, left, right):
    # sort array[left:right+1] (i.e. bounds included)
    if right > left:
        pivotnewindex = partition(array, left, right)
        quicksort(array, left, pivotnewindex - 1)
        quicksort(array, pivotnewindex + 1, right)

def sort_descrs(lst):
    quicksort(lst, 0, len(lst)-1)
