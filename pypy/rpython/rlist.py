from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeList, SomeInteger
from pypy.rpython.lltype import *
from pypy.rpython.rtyper import receive, receiveconst
from pypy.rpython.rtyper import peek_at_result_annotation, direct_call

# ____________________________________________________________
#
#  Concrete implementation of RPython lists:
#
#    struct list {
#        items_array *items;
#    }
#
#    'items' points to a C-like array in memory preceded by a 'length' header,
#    where each item contains a primitive value or pointer to the actual list
#    item.

class __extend__(SomeList):

    def lowleveltype(s_list):
        ITEM = s_list.get_s_items().lowleveltype()
        LIST = GcStruct("list", ("items", GcPtr(GcArray(("item", ITEM)))))
        return GcPtr(LIST)

    def get_s_items(s_list):
        return s_list.listdef.listitem.s_value

    def rtype_len(s_lst):
        v_lst = receive(s_lst, arg=0)
        return direct_call(ll_len, v_lst)

    def rtype_method_append(s_lst, s_value):
        v_lst = receive(s_lst, arg=0)
        v_value = receive(s_lst.get_s_items(), arg=1)
        direct_call(ll_append, v_lst, v_value)


class __extend__(pairtype(SomeList, SomeInteger)):

    def rtype_getitem((s_lst1, s_int2)):
        v_lst = receive(s_lst1, arg=0)
        v_index = receive(Signed, arg=1)
        if s_int2.nonneg:
            return direct_call(ll_getitem_nonneg, v_lst, v_index)
        else:
            return direct_call(ll_getitem, v_lst, v_index)


# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

def ll_len(l):
    return len(l.items)

def ll_append(l, newitem):
    length = len(l.items)
    newitems = malloc(typeOf(l).TO.items.TO, length+1)
    i = 0
    while i<length:
        newitems[i].item = l.items[i].item
        i += 1
    newitems[length].item = newitem
    l.items = newitems

def ll_getitem_nonneg(l, i):
    return l.items[i].item

def ll_getitem(l, i):
    if i<0:
        i += len(l.items)
    return l.items[i].item

def ll_setitem_nonneg(l, i, newitem):
    l.items[i].item = newitem

# ____________________________________________________________
#
#  Irregular operations.

def ll_newlist(LISTPTR, length):
    l = malloc(LISTPTR.TO)
    l.items = malloc(LISTPTR.TO.items.TO, length)
    return l

def rtype_newlist(*items_s):
    nb_args = len(items_s)
    s_list = peek_at_result_annotation()
    s_listitem = s_list.get_s_items()
    items_v = [receive(s_listitem, arg=i) for i in range(nb_args)]
    c1 = receiveconst(Void, s_list.lowleveltype())
    v_result = direct_call(ll_newlist, c1, receiveconst(Signed, nb_args))
    for i in range(nb_args):
        direct_call(ll_setitem_nonneg, v_result,
                                       receiveconst(Signed, i),
                                       items_v[i])
    return v_result
