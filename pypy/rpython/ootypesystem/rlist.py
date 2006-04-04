from pypy.annotation.pairtype import pairtype
from pypy.rpython.rlist import AbstractListRepr, rtype_newlist
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst, externalvsinternal
from pypy.rpython.ootypesystem import ootype

class BaseListRepr(AbstractListRepr):

    def __init__(self, rtyper, item_repr, listitem=None):
        self.rtyper = rtyper
        # XXX do we need something like this for ootypes?
        #self.LIST = GcForwardReference()
        if not isinstance(item_repr, Repr):  # not computed yet, done by setup()
            assert callable(item_repr)
            self._item_repr_computer = item_repr
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
            self.lowleveltype = ootype.List(self.item_repr.lowleveltype)

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
    c1 = inputconst(ootype.Void, r_list.lowleveltype)
    v_result = llops.genop("new", [c1], resulttype=r_list.lowleveltype)
    #LIST = r_list.LIST
    #cno = inputconst(Signed, len(items_v))
    #v_result = llops.gendirectcall(LIST.ll_newlist, cno)
    #v_func = inputconst(Void, dum_nocheck)
    #for i, v_item in enumerate(items_v):
    #    ci = inputconst(Signed, i)
    #    llops.gendirectcall(ll_setitem_nonneg, v_func, v_result, ci, v_item)
    return v_result
