from pypy.objspace.std.objspace import *
from intobject import W_IntObject
from sliceobject import W_SliceObject
from instmethobject import W_InstMethObject
from pypy.interpreter.extmodule import make_builtin_func


class W_ListObject(W_Object):

    def __init__(w_self, space, wrappeditems):
        W_Object.__init__(w_self, space)
        w_self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def append(w_self, w_obj):
        w_self.wrappeditems.append(w_obj)
        return w_self.space.w_None


def list_unwrap(space, w_list):
    items = [space.unwrap(w_item) for w_item in w_list.wrappeditems]
    return list(items)

StdObjSpace.unwrap.register(list_unwrap, W_ListObject)

def list_is_true(space, w_list):
    return not not w_list.wrappeditems

StdObjSpace.is_true.register(list_is_true, W_ListObject)

def list_len(space, w_list):
    result = len(w_list.wrappeditems)
    return W_IntObject(space, result)

StdObjSpace.len.register(list_len, W_ListObject)

def getitem_list_int(space, w_list, w_index):
    items = w_list.wrappeditems
    try:
        w_item = items[w_index.intval]
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("list index out of range"))
    return w_item

StdObjSpace.getitem.register(getitem_list_int, W_ListObject, W_IntObject)

def getitem_list_slice(space, w_list, w_slice):
    items = w_list.wrappeditems
    w_length = space.wrap(len(items))
    w_start, w_stop, w_step, w_slicelength = w_slice.indices(space, w_length)
    start       = space.unwrap(w_start)
    step        = space.unwrap(w_step)
    slicelength = space.unwrap(w_slicelength)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = items[start]
        start += step
    return W_ListObject(space, subitems)

StdObjSpace.getitem.register(getitem_list_slice, W_ListObject, W_SliceObject)

def list_iter(space, w_list):
    import iterobject
    return iterobject.W_SeqIterObject(space, w_list)

StdObjSpace.iter.register(list_iter, W_ListObject)

def list_add(space, w_list1, w_list2):
    items1 = w_list1.wrappeditems
    items2 = w_list2.wrappeditems
    return W_ListObject(space, items1 + items2)

StdObjSpace.add.register(list_add, W_ListObject, W_ListObject)

def list_int_mul(space, w_list, w_int):
    items = w_list.wrappeditems
    times = w_int.intval
    return W_ListObject(space, items * times)

StdObjSpace.mul.register(list_int_mul, W_ListObject, W_IntObject)

def list_eq(space, w_list1, w_list2):
    items1 = w_list1.wrappeditems
    items2 = w_list2.wrappeditems
    if len(items1) != len(items2):
        return space.w_False
    for item1, item2 in zip(items1, items2):
        if not space.is_true(space.eq(item1, item2)):
            return space.w_False
    return space.w_True

StdObjSpace.eq.register(list_eq, W_ListObject, W_ListObject)

# upto here, lists are nearly identical to tuples.
# XXX have to add over-allocation!

def getattr_list(space, w_list, w_attr):
    if space.is_true(space.eq(w_attr, space.wrap('append'))):
        w_builtinfn = make_builtin_func(space, W_ListObject.append)
        return W_InstMethObject(space, w_list, w_builtinfn)
    raise FailedToImplement(space.w_AttributeError)

StdObjSpace.getattr.register(getattr_list, W_ListObject, W_ANY)


"""
static PyMethodDef list_methods[] = {
	{"append",	(PyCFunction)listappend,  METH_O, append_doc},
	{"insert",	(PyCFunction)listinsert,  METH_VARARGS, insert_doc},
	{"extend",      (PyCFunction)listextend,  METH_O, extend_doc},
	{"pop",		(PyCFunction)listpop, 	  METH_VARARGS, pop_doc},
	{"remove",	(PyCFunction)listremove,  METH_O, remove_doc},
	{"index",	(PyCFunction)listindex,   METH_O, index_doc},
	{"count",	(PyCFunction)listcount,   METH_O, count_doc},
	{"reverse",	(PyCFunction)listreverse, METH_NOARGS, reverse_doc},
	{"sort",	(PyCFunction)listsort, 	  METH_VARARGS, sort_doc},
	{NULL,		NULL}		/* sentinel */
};
"""
