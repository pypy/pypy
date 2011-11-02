from pypy.interpreter import gateway
from pypy.interpreter.error import OperationError
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.register_all import register_all
from sys import maxint

list_append   = SMM('append', 2,
                    doc='L.append(object) -- append object to end')
list_insert   = SMM('insert', 3,
                    doc='L.insert(index, object) -- insert object before index')
list_extend   = SMM('extend', 2,
                    doc='L.extend(iterable) -- extend list by appending'
                        ' elements from the iterable')
list_pop      = SMM('pop',    2, defaults=(None,),
                    doc='L.pop([index]) -> item -- remove and return item at'
                        ' index (default last)')
list_remove   = SMM('remove', 2,
                    doc='L.remove(value) -- remove first occurrence of value')
list_index    = SMM('index',  4, defaults=(0,maxint),
                    doc='L.index(value, [start, [stop]]) -> integer -- return'
                        ' first index of value')
list_count    = SMM('count',  2,
                    doc='L.count(value) -> integer -- return number of'
                        ' occurrences of value')
list_reverse  = SMM('reverse',1,
                    doc='L.reverse() -- reverse *IN PLACE*')
list_sort     = SMM('sort',   4, defaults=(None, None, False),
                    argnames=['cmp', 'key', 'reverse'],
                    doc='L.sort(cmp=None, key=None, reverse=False) -- stable'
                        ' sort *IN PLACE*;\ncmp(x, y) -> -1, 0, 1')
list_reversed = SMM('__reversed__', 1,
                    doc='L.__reversed__() -- return a reverse iterator over'
                        ' the list')

def list_reversed__ANY(space, w_list):
    from pypy.objspace.std.iterobject import W_ReverseSeqIterObject
    return W_ReverseSeqIterObject(space, w_list, -1)

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_listtype, __args__):
    from pypy.objspace.std.listobject import W_ListObject
    w_obj = space.allocate_instance(W_ListObject, w_listtype)
    W_ListObject.__init__(w_obj, space, [])
    return w_obj

# ____________________________________________________________

list_typedef = StdTypeDef("list",
    __doc__ = '''list() -> new list
list(sequence) -> new list initialized from sequence's items''',
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = None,
    )
list_typedef.registermethods(globals())

# ____________________________________________________________

def get_list_index(space, w_index):
    return space.getindex_w(w_index, space.w_IndexError, "list index")
