from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr
from pypy.rpython import rrange

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

class __extend__(annmodel.SomeList):
    def rtyper_makerepr(self, rtyper):
        listitem = self.listdef.listitem
        if listitem.range_step and not listitem.mutated:
            return rrange.RangeRepr(listitem.range_step)
        else:
            # cannot do the rtyper.getrepr() call immediately, for the case
            # of recursive structures -- i.e. if the listdef contains itself
            return ListRepr(lambda: rtyper.getrepr(listitem.s_value))


class ListRepr(Repr):

    def __init__(self, item_repr):
        self.LIST = GcForwardReference()
        self.lowleveltype = GcPtr(self.LIST)
        self.item_repr = item_repr   # possibly uncomputed at this point!
        # setup() needs to be called to finish this initialization

    def setup(self):
        if callable(self.item_repr):
            self.item_repr = self.item_repr()
        if isinstance(self.LIST, GcForwardReference):
            ITEM = self.item_repr.lowleveltype
            ITEMARRAY = GcArray(("item", ITEM))
            self.LIST.become(GcStruct("list", ("items", GcPtr(ITEMARRAY))))

    def rtype_len(self, hop):
        v_lst, = hop.inputargs(self)
        return hop.gendirectcall(ll_len, v_lst)

    def rtype_method_append(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.gendirectcall(ll_append, v_lst, v_value)

    def make_iterator_repr(self):
        return ListIteratorRepr(self)


class __extend__(pairtype(ListRepr, IntegerRepr)):

    def rtype_getitem((r_lst, r_int), hop):
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        if hop.args_s[1].nonneg:
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

def ll_setitem(l, i, newitem):
    if i<0:
        i += len(l.items)
    l.items[i].item = newitem

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
    r_list = hop.r_result
    r_listitem = r_list.item_repr
    c1 = hop.inputconst(Void, r_list.lowleveltype)
    c2 = hop.inputconst(Signed, nb_args)
    v_result = hop.gendirectcall(ll_newlist, c1, c2)
    for i in range(nb_args):
        ci = hop.inputconst(Signed, i)
        v_item = hop.inputarg(r_listitem, arg=i)
        hop.gendirectcall(ll_setitem_nonneg, v_result, ci, v_item)
    return v_result

# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(Repr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = GcPtr(GcStruct('listiter',
                                           ('list', r_list.lowleveltype),
                                           ('index', Signed)))

    def newiter(self, hop):
        v_lst, = hop.inputargs(self.r_list)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(ll_listiter, citerptr, v_lst)

    def next(self, hop):
        v_iter = hop.inputargs(self)
        return hop.gendirectcall(ll_listnext, v_iter)

def ll_listiter(ITERPTR, lst):
    iter = malloc(ITERPTR.TO)
    iter.list = lst
    iter.index = 0
    return iter

def ll_listnext(iter):
    l = iter.list
    index = iter.index
    if index >= len(l.items):
        raise StopIteration
    iter.index = index + 1
    return l.items[index]
