from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeList, SomeInteger
from pypy.rpython.lltype import *

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

    def rtype_len(s_lst, hop):
        v_lst = hop.inputargs(s_lst)
        return hop.gendirectcall(ll_len, v_lst)

    def rtype_method_append(s_lst, hop):
        v_lst, v_value = hop.inputargs(s_lst, s_lst.get_s_items())
        hop.gendirectcall(ll_append, v_lst, v_value)


class __extend__(pairtype(SomeList, SomeInteger)):

    def rtype_getitem((s_lst1, s_int2), hop):
        v_lst, v_index = hop.inputargs(s_lst1, Signed)
        if s_int2.nonneg:
            llfn = ll_getitem_nonneg
        else:
            llfn = ll_getitem
        return hop.gendirectcall(llfn, v_lst, v_index)


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

def rtype_newlist(hop):
    nb_args = hop.nb_args
    s_list = hop.s_result
    s_listitem = s_list.get_s_items()
    c1 = hop.inputconst(Void, s_list.lowleveltype())
    c2 = hop.inputconst(Signed, nb_args)
    v_result = hop.gendirectcall(ll_newlist, c1, c2)
    for i in range(nb_args):
        ci = hop.inputconst(Signed, i)
        v_item = hop.inputarg(s_listitem, arg=i)
        hop.gendirectcall(ll_setitem_nonneg, v_result, ci, v_item)
    return v_result
