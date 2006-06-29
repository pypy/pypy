from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop
from pypy.jit.timeshifter.rcontainer import AbstractContainer, cachedtype
from pypy.jit.timeshifter import rvalue


class ListTypeDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, LIST):
        self.LIST = LIST
        self.LISTPTR = lltype.Ptr(LIST)
        self.gv_type = rgenop.constTYPE(self.LIST)
        self.gv_ptrtype = rgenop.constTYPE(self.LISTPTR)

    def _freeze_(self):
        return True


class VirtualList(AbstractContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        self.item_boxes = []

    def enter_block(self, newblock, incoming, memo):
        pass

    def force_runtime_container(self, jitstate):
        pass

    def freeze(self, memo):
        pass

    def copy(self, memo):
        pass

    def replace(self, memo):
        pass


def oop_newlist(jitstate, typedesc, lengthbox):
    assert lengthbox.is_constant()
    length = rvalue.ll_getvalue(lengthbox, lltype.Signed)
    assert length == 0
    vlist = VirtualList(typedesc)
    box = rvalue.PtrRedBox(typedesc.gv_ptrtype)
    box.content = vlist
    return box

def oop_list_append(jitstate, selfbox, itembox):
    assert isinstance(selfbox.content, VirtualList)
    selfbox.content.item_boxes.append(itembox)

def oop_list_getitem(jitstate, selfbox, indexbox):
    assert isinstance(selfbox.content, VirtualList)
    assert indexbox.is_constant()
    index = rvalue.ll_getvalue(indexbox, lltype.Signed)
    return selfbox.content.item_boxes[index]
