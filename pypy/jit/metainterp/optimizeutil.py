from pypy.rlib.objectmodel import r_dict, compute_identity_hash
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation

class InvalidLoop(Exception):
    """Raised when the optimize*.py detect that the loop that
    we are trying to build cannot possibly make sense as a
    long-running loop (e.g. it cannot run 2 complete iterations)."""

# ____________________________________________________________
# Misc. utilities

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


def descrlist_hash(l):
    res = 0x345678
    for descr in l:
        y = compute_identity_hash(descr)
        res = intmask((1000003 * res) ^ y)
    return res

def descrlist_eq(l1, l2):
    if len(l1) != len(l2):
        return False
    for i in range(len(l1)):
        if l1[i] is not l2[i]:
            return False
    return True

def descrlist_dict():
    return r_dict(descrlist_eq, descrlist_hash)

