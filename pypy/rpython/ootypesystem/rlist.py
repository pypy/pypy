from pypy.tool.pairtype import pairtype
from pypy.rpython.rlist import AbstractBaseListRepr, AbstractListRepr, \
        AbstractListIteratorRepr, AbstractFixedSizeListRepr, rtype_newlist, rtype_alloc_and_set
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.rmodel import inputconst, externalvsinternal
from pypy.rpython.lltypesystem.lltype import Signed, Void
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem import rstr


class BaseListRepr(AbstractBaseListRepr):
    rstr_ll = rstr.LLHelpers

    def __init__(self, rtyper, item_repr, listitem=None, known_maxlength=False):
        self.rtyper = rtyper
        if not isinstance(item_repr, Repr):
            assert callable(item_repr)
            self._item_repr_computer = item_repr
        else:
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(rtyper, item_repr)
        self.known_maxlength = known_maxlength
        self.LIST = self._make_empty_type()
        self.lowleveltype = self.LIST
        self.listitem = listitem
        self.list_cache = {}
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = \
                    self._externalvsinternal(self.rtyper, self._item_repr_computer())
        if not self._hasItemType(self.lowleveltype):
            self._setItemType(self.lowleveltype, self.item_repr.lowleveltype)

    def _hasItemType(self, LIST):
        return ootype.hasItemType(LIST)

    def _setItemType(self, LIST, ITEM):
        ootype.setItemType(LIST, ITEM)

    def _externalvsinternal(self, rtyper, item_repr):
        return item_repr, item_repr
    
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

    def rtype_hint(self, hop):
        hints = hop.args_s[-1].const
        optimized = getattr(self.listitem, 'hint_maxlength', False)
        if optimized and 'maxlength' in hints:
            return self.rtype_hint_maxlength(hop)
        elif 'fence' in hints:
            return self.rtype_hint_fence(hop)
        return AbstractBaseListRepr.rtype_hint(self, hop)

    def rtype_hint_maxlength(self, hop):
        v_maxlength = self._get_v_maxlength(hop)
        RESLIST = hop.r_result.LIST
        _, ARRAY = RESLIST._lookup_field('items')
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        cARRAY = hop.inputconst(Void, ARRAY)            
        return hop.llops.gendirectcall(ll_newlist_maxlength, cRESLIST, cARRAY, v_maxlength)

    def rtype_hint_fence(self, hop):
        hints = hop.args_s[-1].const
        v_list = hop.inputarg(self, arg=0)
        RESLIST = hop.r_result.LIST
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        if self.known_maxlength:
            if isinstance(hop.r_result, FixedSizeListRepr):
                if 'exactlength' in hints:
                    llfn = ll_known_maxlength2fixed_exact
                else:
                    llfn = ll_known_maxlength2fixed
            else:
                llfn = ll_known_maxlength2list
        else:
            if isinstance(hop.r_result, FixedSizeListRepr):
                llfn = ll_list2fixed
            else:
                return v_list
        return hop.llops.gendirectcall(llfn, cRESLIST, v_list)


class ListRepr(AbstractListRepr, BaseListRepr):

    def _hasItemType(self, LIST):
        if self.known_maxlength:
            _, ARRAY = LIST._lookup_field('items')
            return ootype.hasItemType(ARRAY)
        else:
            return ootype.hasItemType(LIST)

    def _setItemType(self, LIST, ITEM):
        if self.known_maxlength:
            _, ARRAY = LIST._lookup_field('items')
            ootype.setItemType(ARRAY, ITEM)
        else:
            ootype.setItemType(LIST, ITEM)

    def null_const(self):
        return ootype.null(self.LIST)

    def prepare_const(self, n):
        result = self.LIST.ll_newlist(n)
        return result
        
    def make_iterator_repr(self):
        return ListIteratorRepr(self)

    def _make_empty_type(self):
        if self.known_maxlength:
            return ootype.Record({"items": ootype.Array(), "length": ootype.Signed})
        else:
            return ootype.List()

    def _generate_newlist(self, llops, items_v, v_sizehint):
        c_list = inputconst(ootype.Void, self.lowleveltype)
        v_result = llops.genop("new", [c_list], resulttype=self.lowleveltype)
        c_resize = inputconst(ootype.Void, "_ll_resize")
        c_length = inputconst(ootype.Signed, len(items_v))
        llops.genop("oosend", [c_resize, v_result, c_length], resulttype=ootype.Void)
        return v_result

    def rtype_method_append(self, hop):
        if self.known_maxlength:
            v_lst, v_value = hop.inputargs(self, self.item_repr)
            hop.exception_cannot_occur()
            hop.gendirectcall(ll_append_maxlength, v_lst, v_value)
        else:
            return AbstractListRepr.rtype_method_append(self, hop)


class __extend__(pairtype(BaseListRepr, BaseListRepr)):

    def rtype_is_((r_lst1, r_lst2), hop):
        # NB. this version performs no cast to the common base class
        vlist = hop.inputargs(r_lst1, r_lst2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)



def newlist(llops, r_list, items_v, v_sizehint=None):
    v_result = r_list._generate_newlist(llops, items_v, v_sizehint)

    c_setitem = inputconst(ootype.Void, "ll_setitem_fast")
    for i, v_item in enumerate(items_v):
        ci = inputconst(Signed, i)
        llops.genop("oosend", [c_setitem, v_result, ci, v_item], resulttype=ootype.Void)
    return v_result

def ll_newlist(LIST, length):
    lst = ootype.new(LIST)
    lst._ll_resize(length)
    return lst

# lists with known_maxlength
def ll_newlist_maxlength(LIST, ARRAY, length):
    lst = ootype.new(LIST)
    lst.items = ootype.oonewarray(ARRAY, length)
    lst.length = 0
    return lst

def ll_append_maxlength(l, newitem):
    l.items.ll_setitem_fast(l.length, newitem)
    l.length += 1

def ll_known_maxlength2fixed(ARRAY, l):
    n = l.length
    olditems = l.items
    if n == olditems.ll_length():
        return olditems
    else:
        newitems = ootype.oonewarray(ARRAY, n)
        for i in range(n):
            item = olditems.ll_getitem_fast(i)
            newitems.ll_setitem_fast(i, item)
        return newitems

def ll_known_maxlength2fixed_exact(ARRAY, l):
    return l.items

def ll_known_maxlength2list(RESLIST, l):
    res = ootype.new(RESLIST)
    length = l.length
    res._ll_resize_ge(length)
    for i in range(length):
        item = l.items.ll_getitem_fast(i)
        res.ll_setitem_fast(i, item)
    return res

def ll_list2fixed(RESLIST, l):
    length = l.ll_length()
    res = ootype.oonewarray(RESLIST, length)
    for i in range(length):
        item = l.ll_getitem_fast(i)
        res.ll_setitem_fast(i, item)
    return res

# Fixed-size list 
class FixedSizeListRepr(AbstractFixedSizeListRepr, BaseListRepr):
    def compact_repr(self):
        return 'FixedSizeListR %s' % (self.item_repr.compact_repr(),)

    def _make_empty_type(self):
        return ootype.Array()
        
    def null_const(self):
        return self.LIST._null

    def prepare_const(self, n):
        return ll_newarray(self.LIST, n)

    def make_iterator_repr(self):
        return ListIteratorRepr(self)

    def _generate_newlist(self, llops, items_v, v_sizehint):
        c_array = inputconst(ootype.Void, self.lowleveltype)
        c_length = inputconst(ootype.Signed, len(items_v))
        v_result = llops.genop("oonewarray", [c_array, c_length], resulttype=self.lowleveltype)
        return v_result

def ll_newarray(ARRAY, length):
    return ootype.oonewarray(ARRAY, length)

# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(AbstractListIteratorRepr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = ootype.Record(
                {"iterable": r_list.lowleveltype, "index": ootype.Signed})
        self.ll_listiter = ll_listiter
        self.ll_listnext = ll_listnext
        self.ll_getnextindex = ll_getnextindex


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

def ll_getnextindex(iter):
    return iter.index
