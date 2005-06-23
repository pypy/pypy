from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltype import *
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr
from pypy.rpython import rrange
from pypy.rpython.rslice import SliceRepr
from pypy.rpython.rslice import startstop_slice_repr, startonly_slice_repr

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
            return ListRepr(lambda: rtyper.getrepr(listitem.s_value),
                            listitem)
    def rtyper_makekey(self):
        return self.listdef.listitem


class ListRepr(Repr):

    def __init__(self, item_repr, listitem=None):
        self.LIST = GcForwardReference()
        self.lowleveltype = Ptr(self.LIST)
        if not isinstance(item_repr, Repr):  # not computed yet, done by setup()
            assert callable(item_repr)
            self._item_repr_computer = item_repr
        else:
            self.item_repr = item_repr
        self.listitem = listitem
        self.list_cache = {}
        # setup() needs to be called to finish this initialization

    def setup(self):
        if 'item_repr' not in self.__dict__:
            self.item_repr = self._item_repr_computer()
        if isinstance(self.LIST, GcForwardReference):
            ITEM = self.item_repr.lowleveltype
            ITEMARRAY = GcArray(ITEM)
            self.LIST.become(GcStruct("list", ("items", Ptr(ITEMARRAY))))

    def convert_const(self, listobj):
        listobj = getattr(listobj, '__self__', listobj) # for bound list methods
        if not isinstance(listobj, list):
            raise TyperError("expected a list: %r" % (listobj,))
        try:
            key = Constant(listobj)
            return self.list_cache[key]
        except KeyError:
            self.setup()
            result = malloc(self.LIST, immortal=True)
            self.list_cache[key] = result
            result.items = malloc(self.LIST.items.TO, len(listobj))
            r_item = self.item_repr
            for i in range(len(listobj)):
                x = listobj[i]
                result.items[i] = r_item.convert_const(x)
            return result

    def rtype_len(self, hop):
        v_lst, = hop.inputargs(self)
        return hop.gendirectcall(ll_len, v_lst)

    def rtype_method_append(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.gendirectcall(ll_append, v_lst, v_value)

    def rtype_method_insert(self, hop):
        v_lst, v_index, v_value = hop.inputargs(self, Signed, self.item_repr)
        if hop.args_s[1].nonneg:
            llfn = ll_insert_nonneg
        else:
            llfn = ll_insert
        hop.gendirectcall(llfn, v_lst, v_index, v_value)

    def rtype_method_extend(self, hop):
        v_lst1, v_lst2 = hop.inputargs(self, self)
        hop.gendirectcall(ll_extend, v_lst1, v_lst2)
    
    def rtype_method_reverse(self, hop):
        v_lst, = hop.inputargs(self)
        hop.gendirectcall(ll_reverse,v_lst)

    def rtype_method_pop(self, hop):
        if hop.nb_args == 2:
            v_list, v_index = hop.inputargs(self, Signed)
            if hop.args_s[1].nonneg:
                llfn = ll_pop_nonneg
            else:
                llfn = ll_pop
        else:
            v_list, = hop.inputargs(self)
            v_index = hop.inputconst(Signed, -1)
            llfn = ll_pop
        assert hasattr(v_index, 'concretetype')
        return hop.gendirectcall(llfn, v_list, v_index)

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
    
##    def rtype_method_pop((r_list,r_int),hop):
##        v_lst, v_index = hop.inputargs(r_lst, Signed)
##        return hop.gendirectcall(ll_pop,v_list,v_index)
    
    def rtype_setitem((r_lst, r_int), hop):
        v_lst, v_index, v_item = hop.inputargs(r_lst, Signed, r_lst.item_repr)
        if hop.args_s[1].nonneg:
            llfn = ll_setitem_nonneg
        else:
            llfn = ll_setitem
        return hop.gendirectcall(llfn, v_lst, v_index, v_item)

    def rtype_delitem((r_lst, r_int), hop):
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        if hop.args_s[1].nonneg:
            llfn = ll_delitem_nonneg
        else:
            llfn = ll_delitem
        return hop.gendirectcall(llfn, v_lst, v_index)

class __extend__(pairtype(ListRepr, SliceRepr)):

    def rtype_getitem((r_lst, r_slic), hop):
        if r_slic == startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, startonly_slice_repr)
            return hop.gendirectcall(ll_listslice_startonly, v_lst, v_start)
        if r_slic == startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, startstop_slice_repr)
            return hop.gendirectcall(ll_listslice, v_lst, v_slice)
        raise TyperError(r_slic)

    def rtype_delitem((r_lst, r_slic), hop):
        if r_slic == startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, startonly_slice_repr)
            hop.gendirectcall(ll_listdelslice_startonly, v_lst, v_start)
            return
        if r_slic == startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, startstop_slice_repr)
            hop.gendirectcall(ll_listdelslice, v_lst, v_slice)
            return
        raise TyperError(r_slic)

class __extend__(pairtype(ListRepr, ListRepr)):
    def convert_from_to((r_lst1, r_lst2), v, llops):
        if r_lst1.listitem is None or r_lst2.listitem is None:
            return NotImplemented
        if r_lst1.listitem is not r_lst2.listitem:
            return NotImplemented
        return v

    def rtype_add((self, _), hop):
        v_lst1, v_lst2 = hop.inputargs(self, self)
        return hop.gendirectcall(ll_concat, v_lst1, v_lst2)

    def rtype_inplace_add((self, _), hop):
        v_lst1, v_lst2 = hop.inputargs(self, self)
        hop.gendirectcall(ll_extend, v_lst1, v_lst2)
        return v_lst1

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
    while i < length:
        newitems[i] = l.items[i]
        i += 1
    newitems[length] = newitem
    l.items = newitems

def ll_insert_nonneg(l, index, newitem):
    length = len(l.items)
    newitems = malloc(typeOf(l).TO.items.TO, length+1)
    i = 0
    while i < index:
        newitems[i] = l.items[i]
        i += 1
    newitems[i] = newitem
    i += 1
    while i <= length:
        newitems[i] = l.items[i-1]
        i += 1
    l.items = newitems

def ll_insert(l, index, newitem):
    if index < 0:
        index += len(l.items)
    ll_insert_nonneg(l, index, newitem)

def ll_pop_nonneg(l, index):
    res = l.items[index]
    ll_delitem_nonneg(l, index)
    return res

def ll_pop(l, index):
    if index < 0:
        index += len(l.items)
    res = l.items[index]
    ll_delitem_nonneg(l, index)
    return res

def ll_reverse(l):
    length = len(l.items)
    len2 = length // 2 # moved this out of the loop
    i = 0
    while i < len2:
        tmp = l.items[i]
        l.items[i] = l.items[length-1-i]
        l.items[length-1-i] = tmp
        i += 1

def ll_getitem_nonneg(l, i):
    return l.items[i]

def ll_getitem(l, i):
    if i < 0:
        i += len(l.items)
    return l.items[i]

def ll_setitem_nonneg(l, i, newitem):
    l.items[i] = newitem

def ll_setitem(l, i, newitem):
    if i < 0:
        i += len(l.items)
    l.items[i] = newitem

def ll_delitem_nonneg(l, i):
    newlength = len(l.items) - 1
    newitems = malloc(typeOf(l).TO.items.TO, newlength)
    j = 0
    while j < i:
        newitems[j] = l.items[j]
        j += 1
    while j < newlength:
        newitems[j] = l.items[j+1]
        j += 1
    l.items = newitems

def ll_delitem(l, i):
    if i < 0:
        i += len(l.items)
    ll_delitem_nonneg(l, i)

def ll_concat(l1, l2):
    len1 = len(l1.items)
    len2 = len(l2.items)
    newitems = malloc(typeOf(l1).TO.items.TO, len1 + len2)
    j = 0
    while j < len1:
        newitems[j] = l1.items[j]
        j += 1
    i = 0
    while i < len2:
        newitems[j] = l2.items[i]
        i += 1
        j += 1
    l = malloc(typeOf(l1).TO)
    l.items = newitems
    return l

def ll_extend(l1, l2):
    len1 = len(l1.items)
    len2 = len(l2.items)
    newitems = malloc(typeOf(l1).TO.items.TO, len1 + len2)
    j = 0
    while j < len1:
        newitems[j] = l1.items[j]
        j += 1
    i = 0
    while i < len2:
        newitems[j] = l2.items[i]
        i += 1
        j += 1
    l1.items = newitems

def ll_listslice_startonly(l1, start):
    len1 = len(l1.items)
    newitems = malloc(typeOf(l1).TO.items.TO, len1 - start)
    j = 0
    while start < len1:
        newitems[j] = l1.items[start]
        start += 1
        j += 1
    l = malloc(typeOf(l1).TO)
    l.items = newitems
    return l

def ll_listslice(l1, slice):
    start = slice.start
    stop = slice.stop
    newitems = malloc(typeOf(l1).TO.items.TO, stop - start)
    j = 0
    while start < stop:
        newitems[j] = l1.items[start]
        start += 1
        j += 1
    l = malloc(typeOf(l1).TO)
    l.items = newitems
    return l

def ll_listdelslice_startonly(l1, start):
    newitems = malloc(typeOf(l1).TO.items.TO, start)
    j = 0
    while j < start:
        newitems[j] = l1.items[j]
        j += 1
    l1.items = newitems

def ll_listdelslice(l1, slice):
    start = slice.start
    stop = slice.stop
    newlength = len(l1.items) - (stop-start)
    newitems = malloc(typeOf(l1).TO.items.TO, newlength)
    j = 0
    while j < start:
        newitems[j] = l1.items[j]
        j += 1
    while j < newlength:
        newitems[j] = l1.items[stop]
        stop += 1
        j += 1
    l1.items = newitems

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

def ll_alloc_and_set(LISTPTR, count, item):
    l = malloc(LISTPTR.TO)
    l.items = malloc(LISTPTR.TO.items.TO, count)
    i = 0
    while i < count:
        l.items[i] = item
        i += 1
    return l

def rtype_alloc_and_set(hop):
    r_list = hop.r_result
    v_count, v_item = hop.inputargs(Signed, r_list.item_repr)
    c1 = hop.inputconst(Void, r_list.lowleveltype)
    return hop.gendirectcall(ll_alloc_and_set, c1, v_count, v_item)

# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(Repr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = Ptr(GcStruct('listiter',
                                         ('list', r_list.lowleveltype),
                                         ('index', Signed)))

    def newiter(self, hop):
        v_lst, = hop.inputargs(self.r_list)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(ll_listiter, citerptr, v_lst)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
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
