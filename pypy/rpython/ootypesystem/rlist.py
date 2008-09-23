from pypy.tool.pairtype import pairtype
from pypy.rpython.rlist import AbstractBaseListRepr, AbstractListRepr, \
        AbstractListIteratorRepr, AbstractFixedSizeListRepr, rtype_newlist, rtype_alloc_and_set
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.rmodel import inputconst, externalvsinternal
from pypy.rpython.lltypesystem.lltype import Signed, Void
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.rslice import SliceRepr, \
     startstop_slice_repr, startonly_slice_repr, minusone_slice_repr
from pypy.rpython.ootypesystem import rstr


class BaseListRepr(AbstractBaseListRepr):
    rstr_ll = rstr.LLHelpers

    def __init__(self, rtyper, item_repr, listitem=None):
        self.rtyper = rtyper
        if not isinstance(item_repr, Repr):
            assert callable(item_repr)
            self._item_repr_computer = item_repr
        else:
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(rtyper, item_repr)
        self.LIST = self._make_empty_type()
        self.lowleveltype = self.LIST
        self.listitem = listitem
        self.list_cache = {}
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = \
                    self._externalvsinternal(self.rtyper, self._item_repr_computer())
        if not ootype.hasItemType(self.lowleveltype):
            ootype.setItemType(self.lowleveltype, self.item_repr.lowleveltype)

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
        if 'maxlength' in hints or 'fence' in hints:
            # see doc/discussion/list_comprehension_ootype.txt
            assert False, 'TODO'
        return AbstractBaseListRepr.rtype_hint(self, hop)


class ListRepr(AbstractListRepr, BaseListRepr):
    def null_const(self):
        return self.LIST._null

    def prepare_const(self, n):
        result = self.LIST.ll_newlist(n)
        return result
        
    def make_iterator_repr(self):
        return ListIteratorRepr(self)

    def _make_empty_type(self):
        return ootype.List()

    def _generate_newlist(self, llops, items_v):
        c_list = inputconst(ootype.Void, self.lowleveltype)
        v_result = llops.genop("new", [c_list], resulttype=self.lowleveltype)
        c_resize = inputconst(ootype.Void, "_ll_resize")
        c_length = inputconst(ootype.Signed, len(items_v))
        llops.genop("oosend", [c_resize, v_result, c_length], resulttype=ootype.Void)
        return v_result

class __extend__(pairtype(BaseListRepr, BaseListRepr)):

    def rtype_is_((r_lst1, r_lst2), hop):
        # NB. this version performs no cast to the common base class
        vlist = hop.inputargs(r_lst1, r_lst2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)



def newlist(llops, r_list, items_v):
    v_result = r_list._generate_newlist(llops, items_v)

    c_setitem = inputconst(ootype.Void, "ll_setitem_fast")
    for i, v_item in enumerate(items_v):
        ci = inputconst(Signed, i)
        llops.genop("oosend", [c_setitem, v_result, ci, v_item], resulttype=ootype.Void)
    return v_result

def ll_newlist(LIST, length):
    lst = ootype.new(LIST)
    lst._ll_resize(length)
    return lst

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

    def _generate_newlist(self, llops, items_v):
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

