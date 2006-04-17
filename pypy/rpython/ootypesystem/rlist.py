from pypy.annotation.pairtype import pairtype
from pypy.rpython.rlist import AbstractBaseListRepr, AbstractListRepr, \
        AbstractListIteratorRepr, rtype_newlist
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.rmodel import inputconst, externalvsinternal
from pypy.rpython.lltypesystem.lltype import Signed, Void
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.riterable import iterator_type
from pypy.rpython.ootypesystem.rslice import SliceRepr, \
     startstop_slice_repr, startonly_slice_repr, minusone_slice_repr


class BaseListRepr(AbstractBaseListRepr):

    def __init__(self, rtyper, item_repr, listitem=None):
        self.rtyper = rtyper
        if not isinstance(item_repr, Repr):  # not computed yet, done by setup()
            assert callable(item_repr)
            self._item_repr_computer = item_repr
            self.LIST = ootype.ForwardReference()
        else:
            self.LIST = ootype.List(item_repr.lowleveltype)
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(rtyper, item_repr)
        self.lowleveltype = self.LIST
        self.listitem = listitem
        self.list_cache = {}
##        self.ll_concat = ll_concat
##        self.ll_extend = ll_extend
##        self.ll_listslice_startonly = ll_listslice_startonly
##        self.ll_listslice = ll_listslice
##        self.ll_listslice_minusone = ll_listslice_minusone
##        self.ll_listsetslice = ll_listsetslice
##        self.ll_listdelslice_startonly = ll_listdelslice_startonly
##        self.ll_listdelslice = ll_listdelslice
##        self.ll_listindex = ll_listindex
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.lowleveltype, ootype.ForwardReference):
            self.lowleveltype.become(ootype.List(self.item_repr.lowleveltype))

    def send_message(self, hop, message, can_raise=False, v_args=None):
        if v_args is None:
            v_args = hop.inputargs(self, *hop.args_r[1:])
        c_name = hop.inputconst(ootype.Void, message)
        if can_raise:
            hop.exception_is_here()
        return hop.genop("oosend", [c_name] + v_args,
                resulttype=hop.r_result.lowleveltype)

    def get_eqfunc(self):
        return inputconst(Void, self.item_repr.get_ll_eq_function())

##    def rtype_len(self, hop):
##        return self.send_message(hop, "ll_length")

##    def rtype_is_true(self, hop):
##        v_lst, = hop.inputargs(self)
##        return hop.gendirectcall(ll_list_is_true, v_lst)

##    def rtype_bltn_list(self, hop):
##        v_lst = hop.inputarg(self, 0)        
##        c_start = hop.inputconst(Signed, 0)
##        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)        
##        return hop.gendirectcall(self.ll_listslice_startonly, cRESLIST, v_lst, c_start)

##    def rtype_method_append(self, hop):
##        return self.send_message(hop, "append")

##    def rtype_method_extend(self, hop):
##        return self.send_message(hop, "extend")

    def make_iterator_repr(self):
        return ListIteratorRepr(self)

class ListRepr(AbstractListRepr, BaseListRepr):

    pass

FixedSizeListRepr = ListRepr

##class __extend__(pairtype(BaseListRepr, IntegerRepr)):

##    def rtype_getitem((r_list, r_int), hop):
##        if hop.args_s[1].nonneg:
##            return r_list.send_message(hop, "ll_getitem_fast", can_raise=True)
##        else:
##            v_list, v_index = hop.inputargs(r_list, Signed)            
##            hop.exception_is_here()
##            v_res = hop.gendirectcall(ll_getitem, v_list, v_index)
##            return r_list.recast(hop.llops, v_res)

##    def rtype_setitem((r_list, r_int), hop):
##        if hop.args_s[1].nonneg:
##            return r_list.send_message(hop, "ll_setitem_fast", can_raise=True)
##        else:
##            v_list, v_index, v_item = hop.inputargs(r_list, Signed, r_list.item_repr)
##            hop.exception_is_here()
##            return hop.gendirectcall(ll_setitem, v_list, v_index, v_item)


##class __extend__(pairtype(ListRepr, IntegerRepr)):

##    def rtype_delitem((r_list, r_int), hop):
##        v_list, v_index = hop.inputargs(r_list, Signed)
##        if hop.args_s[1].nonneg:
##            c_count = hop.inputconst(Signed, 1)
##            return r_list.send_message(hop, "remove_range",can_raise=True,
##                                       v_args=[v_list, v_index, c_count])
##        else:
##            hop.exception_is_here()
##            return hop.gendirectcall(ll_delitem, v_list, v_index)


def newlist(llops, r_list, items_v):
    c_1ist = inputconst(ootype.Void, r_list.lowleveltype)
    v_result = llops.genop("new", [c_1ist], resulttype=r_list.lowleveltype)
    c_append = inputconst(ootype.Void, "append")
    # This is very inefficient for a large amount of initial items ...
    for v_item in items_v:
        llops.genop("oosend", [c_append, v_result, v_item],
                resulttype=ootype.Void)
    return v_result

# These helpers are sometimes trivial but help encapsulation

##def ll_newlist(LIST):
##    return ootype.new(LIST)

##def ll_getitem(lst, index):
##    if index < 0:
##        index += lst.ll_length()
##    return lst.ll_getitem_fast(index)

##def ll_setitem(lst, index, item):
##    if index < 0:
##        index += lst.ll_length()
##    return lst.ll_setitem_fast(index, item)

##def ll_delitem(lst, index):
##    if index < 0:
##        index += lst.ll_length()
##    return lst.remove_range(index, 1)

##def ll_list_is_true(lst):
##    return bool(lst) and lst.ll_length() != 0    

##def ll_append(lst, item):
##    lst.append(item)

##def ll_extend(l1, l2):
##    # This is a bit inefficient, could also add extend to the list interface
##    len2 = l2.ll_length()
##    i = 0
##    while i < len2:
##        l1.append(l2.ll_getitem_fast(i))
##        i += 1


##def ll_listslice_startonly(RESLIST, lst, start):
##    len1 = lst.ll_length()
##    #newlength = len1 - start
##    res = ootype.new(RESLIST) # TODO: pre-allocate newlength elements
##    i = start
##    while i < len1:
##        res.append(lst.ll_getitem_fast(i))
##        i += 1
##    return res

##def ll_listslice(RESLIST, lst, slice):
##    start = slice.start
##    stop = slice.stop
##    length = lst.ll_length()
##    if stop > length:
##        stop = length
##    #newlength = stop - start
##    res = ootype.new(RESLIST) # TODO: pre-allocate newlength elements
##    i = start
##    while i < stop:
##        res.append(lst.ll_getitem_fast(i))
##        i += 1
##    return res

##def ll_listslice_minusone(RESLIST, lst):
##    newlength = lst.ll_length() - 1
##    #assert newlength >= 0 # TODO: asserts seems to have problems with ootypesystem
##    res = ootype.new(RESLIST) # TODO: pre-allocate newlength elements
##    i = 0
##    while i < newlength:
##        res.append(lst.ll_getitem_fast(i))
##        i += 1
##    return res

##def ll_listsetslice(l1, slice, l2):
##    count = l2.ll_length()
####    assert count == slice.stop - slice.start, (    # TODO: see above
####        "setslice cannot resize lists in RPython")
##    # XXX but it should be easy enough to support, soon
##    start = slice.start
##    j = start
##    i = 0
##    while i < count:
##        l1.ll_setitem_fast(j, l2.ll_getitem_fast(i))
##        i += 1
##        j += 1

##def ll_listdelslice_startonly(lst, start):
##    count = lst.ll_length() - start
##    if count > 0:
##        lst.remove_range(start, count)

##def ll_listdelslice(lst, slice):
##    start = slice.start
##    stop = slice.stop
##    length = lst.ll_length()
##    if stop > length:
##        stop = length
##    count = stop - start
##    if count > 0:
##        lst.remove_range(start, count)

##def ll_listindex(lst, obj, eqfn):
##    lng = lst.ll_length()
##    j = 0
##    while j < lng:
##        if eqfn is None:
##            if lst.ll_getitem_fast(j) == obj:
##                return j
##        else:
##            if eqfn(lst.ll_getitem_fast(j), obj):
##                return j
##        j += 1
##    raise ValueError # can't say 'list.index(x): x not in list'



# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(AbstractListIteratorRepr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = iterator_type(r_list, r_list.item_repr)
        self.ll_listiter = ll_listiter
        self.ll_listnext = ll_listnext


def ll_listiter(ITER, lst):
    iter = ootype.new(ITER)
    iter.iterable = lst
    iter.index = 0
    return iter

def ll_listnext(iter):
    l = iter.iterable
    index = iter.index
    if index >= l.ll_length():
        raise StopIteration
    iter.index = index + 1
    return l.ll_getitem_fast(index)

