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

    def null_const(self):
        return self.LIST._null

    def prepare_const(self, n):
        result = self.LIST.ll_newlist(n)
        return result
        

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

    def make_iterator_repr(self):
        return ListIteratorRepr(self)

class ListRepr(AbstractListRepr, BaseListRepr):

    pass

FixedSizeListRepr = ListRepr

class __extend__(pairtype(BaseListRepr, BaseListRepr)):

    def rtype_is_((r_lst1, r_lst2), hop):
        # NB. this version performs no cast to the common base class
        vlist = hop.inputargs(r_lst1, r_lst2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)



def newlist(llops, r_list, items_v):
    c_1ist = inputconst(ootype.Void, r_list.lowleveltype)
    v_result = llops.genop("new", [c_1ist], resulttype=r_list.lowleveltype)
    c_append = inputconst(ootype.Void, "append")
    # This is very inefficient for a large amount of initial items ...
    for v_item in items_v:
        llops.genop("oosend", [c_append, v_result, v_item],
                resulttype=ootype.Void)
    return v_result



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

