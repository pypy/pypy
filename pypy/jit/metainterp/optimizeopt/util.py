from pypy.rlib.objectmodel import r_dict, compute_identity_hash
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.metainterp import resoperation, history
from pypy.jit.metainterp.jitexc import JitException
from pypy.rlib.debug import make_sure_not_resized

# ____________________________________________________________
# Misc. utilities

def _findall(Class, name_prefix, op_prefix=None):
    result = []
    for name in dir(Class):
        if name.startswith(name_prefix):
            opname = name[len(name_prefix):]
            if opname.isupper():
                assert hasattr(resoperation.rop, opname)
    for value, name in resoperation.opname.items():
        if op_prefix and not name.startswith(op_prefix):
            continue
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

# ____________________________________________________________

def args_eq(args1, args2):
    make_sure_not_resized(args1)
    make_sure_not_resized(args2)
    if len(args1) != len(args2):
        return False
    for i in range(len(args1)):
        arg1 = args1[i]
        arg2 = args2[i]
        if isinstance(arg1, history.Const):
            if arg1.__class__ is not arg2.__class__:
                return False
            if not arg1.same_constant(arg2):
                return False
        else:
            if not arg1 is arg2:
                return False
    return True

def args_hash(args):
    make_sure_not_resized(args)
    res = 0x345678
    for arg in args:
        if arg is None:
            y = 17
        elif isinstance(arg, history.Const):
            y = arg._get_hash_()
        else:
            y = compute_identity_hash(arg)
        res = intmask((1000003 * res) ^ y)
    return res

def args_dict():
    return r_dict(args_eq, args_hash)

def args_dict_box():
    return r_dict(args_eq, args_hash)
