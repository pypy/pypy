from pypy.objspace.std.objspace import *
from intobject import W_IntObject
from sliceobject import W_SliceObject
from instmethobject import W_InstMethObject
from pypy.interpreter.extmodule import make_builtin_func
from restricted_int import r_int, r_uint

class W_ListObject(W_Object):

    def __init__(w_self, space, wrappeditems):
        W_Object.__init__(w_self, space)
        w_self.ob_item = []
        w_self.ob_size = 0
        newlen = len(wrappeditems)
        list_resize(w_self, newlen)
        w_self.ob_size = newlen
        items = w_self.ob_item
        p = newlen
        while p:
            p -= 1
            items[p] = wrappeditems[p]

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.ob_item[:self.ob_size]]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def append(w_self, w_obj):
        return list_append(w_self.space, w_self, w_obj)

    def insert(w_self, w_idx, w_obj):
        return list_insert(w_self.space, w_self, w_idx, w_obj)


def list_unwrap(space, w_list):
    items = [space.unwrap(w_item) for w_item in w_list.ob_item[:w_list.ob_size]]
    return list(items)

StdObjSpace.unwrap.register(list_unwrap, W_ListObject)

def list_is_true(space, w_list):
    return not not w_list.ob_size

StdObjSpace.is_true.register(list_is_true, W_ListObject)

def list_len(space, w_list):
    result = w_list.ob_size
    return W_IntObject(space, result)

StdObjSpace.len.register(list_len, W_ListObject)

def getitem_list_int(space, w_list, w_index):
    items = w_list.ob_item
    idx = w_index.intval
    if idx < 0: idx += w_list.ob_size
    if idx < 0 or idx >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    w_item = items[idx]
    return w_item

StdObjSpace.getitem.register(getitem_list_int, W_ListObject, W_IntObject)

def getitem_list_slice(space, w_list, w_slice):
    items = w_list.ob_item
    w_length = space.wrap(w_list.ob_size)
    w_start, w_stop, w_step, w_slicelength = w_slice.indices(space, w_length)
    start       = space.unwrap(w_start)
    step        = space.unwrap(w_step)
    slicelength = space.unwrap(w_slicelength)
    assert slicelength >= 0
    w_res = W_ListObject(space, [])
    list_resize(w_res, slicelength)
    subitems = w_res.ob_item
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    w_res.ob_size = slicelength
    return w_res

StdObjSpace.getitem.register(getitem_list_slice, W_ListObject, W_SliceObject)

def list_iter(space, w_list):
    import iterobject
    return iterobject.W_SeqIterObject(space, w_list)

StdObjSpace.iter.register(list_iter, W_ListObject)

def list_add(space, w_list1, w_list2):
    w_res = W_ListObject(space, [])
    newlen = w_list1.ob_size + w_list2.ob_size
    list_resize(w_res, newlen)
    p = 0
    items = w_res.ob_item
    src = w_list1.ob_item
    for i in range(w_list1.ob_size):
        items[p] = src[i]
        p += 1
    src = w_list2.ob_item
    for i in range(w_list2.ob_size):
        items[p] = src[i]
        p += 1
    w_res.ob_size = p
    return w_res

StdObjSpace.add.register(list_add, W_ListObject, W_ListObject)

def list_int_mul(space, w_list, w_int):
    w_res = W_ListObject(space, [])
    times = w_int.intval
    src = w_list.ob_item
    size = w_list.ob_size
    newlen = size * times  # XXX check overflow
    list_resize(w_res, newlen)
    items = w_res.ob_item
    p = 0
    for _ in range(times):
        for i in range(size):
            items[p] = src[i]
            p += 1
    w_res.ob_size = p
    return w_res

StdObjSpace.mul.register(list_int_mul, W_ListObject, W_IntObject)

def int_list_mul(space, w_int, w_list):
    return list_int_mul(space, w_list, w_int)

StdObjSpace.mul.register(int_list_mul, W_IntObject, W_ListObject)

def list_eq(space, w_list1, w_list2):
    items1 = w_list1.ob_item
    items2 = w_list2.ob_item
    if w_list1.ob_size != w_list2.ob_size:
        return space.w_False
    for i in range(w_list1.ob_size):
        if not space.is_true(space.eq(items1[i], items2[i])):
            return space.w_False
    return space.w_True

StdObjSpace.eq.register(list_eq, W_ListObject, W_ListObject)

# upto here, lists are nearly identical to tuples, despite the
# fact that we now support over-allocation!

def setitem_list_int(space, w_list, w_index, w_any):
    items = w_list.ob_item
    idx = w_index.intval
    if idx < 0: idx += w_list.ob_size
    if idx < 0 or idx >= w_list.ob_size:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    items[idx] = w_any
    return space.w_None

StdObjSpace.setitem.register(setitem_list_int, W_ListObject, W_IntObject, W_ANY)

# not trivial!
def setitem_list_slice(space, w_list, w_slice, w_list2):
    items = w_list.ob_item
    w_length = space.wrap(w_list.ob_size)
    w_start, w_stop, w_step, w_slicelength = w_slice.indices(space, w_length)
    start       = space.unwrap(w_start)
    step        = space.unwrap(w_step)
    slicelength = space.unwrap(w_slicelength)
    assert slicelength >= 0
    w_res = W_ListObject(space, [])
    list_resize(w_res, slicelength)
    subitems = w_res.ob_item
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    w_res.ob_size = slicelength
    return w_res

StdObjSpace.setitem.register(setitem_list_slice, W_ListObject, W_SliceObject, W_ANY)

def getattr_list(space, w_list, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('append'))):
        w_builtinfn = make_builtin_func(space, W_ListObject.append)
        return W_InstMethObject(space, w_list, w_builtinfn)
    if space.is_true(space.eq(w_attr, space.wrap('insert'))):
        w_builtinfn = make_builtin_func(space, W_ListObject.insert)
        return W_InstMethObject(space, w_list, w_builtinfn)
    raise FailedToImplement(space.w_AttributeError)

StdObjSpace.getattr.register(getattr_list, W_ListObject, W_ANY)

# adapted C code
def roundupsize(n):
    nbits = r_uint(0)
    n2 = n >> 5

##    /* Round up:
##     * If n <       256, to a multiple of        8.
##     * If n <      2048, to a multiple of       64.
##     * If n <     16384, to a multiple of      512.
##     * If n <    131072, to a multiple of     4096.
##     * If n <   1048576, to a multiple of    32768.
##     * If n <   8388608, to a multiple of   262144.
##     * If n <  67108864, to a multiple of  2097152.
##     * If n < 536870912, to a multiple of 16777216.
##     * ...
##     * If n < 2**(5+3*i), to a multiple of 2**(3*i).
##     *
##     * This over-allocates proportional to the list size, making room
##     * for additional growth.  The over-allocation is mild, but is
##     * enough to give linear-time amortized behavior over a long
##     * sequence of appends() in the presence of a poorly-performing
##     * system realloc() (which is a reality, e.g., across all flavors
##     * of Windows, with Win9x behavior being particularly bad -- and
##     * we've still got address space fragmentation problems on Win9x
##     * even with this scheme, although it requires much longer lists to
##     * provoke them than it used to).
##     */
    while 1:
        n2 >>= 3
        nbits += 3
        if not n2 :
            break
    return ((n >> nbits) + 1) << nbits

# before we have real arrays,
# we use lists, allocated to fixed size.
# XXX memory overflow is ignored here.
# See listobject.c for reference.

for_later = """
#define NRESIZE(var, type, nitems)              \
do {                                \
    size_t _new_size = roundupsize(nitems);         \
    if (_new_size <= ((~(size_t)0) / sizeof(type)))     \
        PyMem_RESIZE(var, type, _new_size);     \
    else                            \
        var = NULL;                 \
} while (0)
"""

def list_resize(w_list, newlen):
    if newlen > len(w_list.ob_item):
        true_size = roundupsize(newlen)
        old_items = w_list.ob_item
        w_list.ob_item = items = [None] * true_size
        for p in range(len(old_items)):
            items[p] = old_items[p]

def ins1(w_list, where, w_any):
    print w_list.ob_size, w_list.ob_item
    list_resize(w_list, w_list.ob_size+1)
    print w_list.ob_size, w_list.ob_item
    size = w_list.ob_size
    items = w_list.ob_item
    if where < 0:
        where += size
    if where < 0:
        where = 0
    if (where > size):
        where = size
    for i in range(size, where, -1):
        items[i] = items[i-1]
    print w_list.ob_size, w_list.ob_item
    items[where] = w_any
    print w_list.ob_size, w_list.ob_item
    w_list.ob_size += 1
    print w_list.ob_size, w_list.ob_item

def list_insert(space, w_list, w_where, w_any):
    ins1(w_list, w_where.intval, w_any)
    return space.w_None

def list_append(space, w_list, w_any):
    ins1(w_list, w_list.ob_size, w_any)
    return space.w_None

"""
static PyMethodDef list_methods[] = {
    {"append",  (PyCFunction)listappend,  METH_O, append_doc},
    {"insert",  (PyCFunction)listinsert,  METH_VARARGS, insert_doc},
    {"extend",      (PyCFunction)listextend,  METH_O, extend_doc},
    {"pop",     (PyCFunction)listpop,     METH_VARARGS, pop_doc},
    {"remove",  (PyCFunction)listremove,  METH_O, remove_doc},
    {"index",   (PyCFunction)listindex,   METH_O, index_doc},
    {"count",   (PyCFunction)listcount,   METH_O, count_doc},
    {"reverse", (PyCFunction)listreverse, METH_NOARGS, reverse_doc},
    {"sort",    (PyCFunction)listsort,    METH_VARARGS, sort_doc},
    {NULL,      NULL}       /* sentinel */
};
"""
