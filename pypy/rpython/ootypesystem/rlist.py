from pypy.annotation.pairtype import pairtype
from pypy.rpython.rlist import AbstractListRepr, AbstractListIteratorRepr, \
        rtype_newlist
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.rmodel import inputconst, externalvsinternal
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.riterable import iterator_type

class BaseListRepr(AbstractListRepr):

    def __init__(self, rtyper, item_repr, listitem=None):
        self.rtyper = rtyper
        # XXX do we need something like this for ootypes?
        #self.LIST = GcForwardReference()
        if not isinstance(item_repr, Repr):  # not computed yet, done by setup()
            assert callable(item_repr)
            self._item_repr_computer = item_repr
            self.lowleveltype = ootype.ForwardReference()
        else:
            self.lowleveltype = ootype.List(item_repr.lowleveltype)
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(rtyper, item_repr)
        self.listitem = listitem
        self.list_cache = {}
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = \
                    externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.lowleveltype, ootype.ForwardReference):
            self.lowleveltype.become(ootype.List(self.item_repr.lowleveltype))

    def send_message(self, hop, message, can_raise=False):
        v_args = hop.inputargs(self, *hop.args_r[1:])
        c_name = hop.inputconst(ootype.Void, message)
        if can_raise:
            hop.exception_is_here()
        return hop.genop("oosend", [c_name] + v_args,
                resulttype=hop.r_result.lowleveltype)

    def rtype_len(self, hop):
        return self.send_message(hop, "length")

    def rtype_method_append(self, hop):
        return self.send_message(hop, "append")

    def make_iterator_repr(self):
        return ListIteratorRepr(self)

ListRepr = BaseListRepr
FixedSizeListRepr = BaseListRepr

class __extend__(pairtype(BaseListRepr, IntegerRepr)):

    def rtype_getitem((r_list, r_int), hop):
        # XXX must handle negative indices
        return r_list.send_message(hop, "getitem", can_raise=True)

    def rtype_setitem((r_list, r_int), hop):
        # XXX must handle negative indices
        return r_list.send_message(hop, "setitem", can_raise=True)

def newlist(llops, r_list, items_v):
    c_1ist = inputconst(ootype.Void, r_list.lowleveltype)
    v_result = llops.genop("new", [c_1ist], resulttype=r_list.lowleveltype)
    c_append = inputconst(ootype.Void, "append")
    # This is very inefficient for a large amount of initial items ...
    for v_item in items_v:
        llops.genop("oosend", [c_append, v_result, v_item],
                resulttype=ootype.Void)
    return v_result

# These helpers are trivial but help encapsulation

def ll_newlist(LIST):
    return ootype.new(LIST)

def ll_append(lst, item):
    lst.append(item)

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
    if index >= l.length():
        raise StopIteration
    iter.index = index + 1
    return l.getitem(index)

