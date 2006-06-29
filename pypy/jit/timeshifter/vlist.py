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

    def ll_factory(self):
        vlist = VirtualList(self)
        box = rvalue.PtrRedBox(self.gv_ptrtype)
        box.content = vlist
        vlist.ownbox = box
        return box


class FrozenVirtualList(AbstractContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_item_boxes initialized later

    def exactmatch(self, vlist, outgoingvarboxes, memo):
        contmemo = memo.containers
        if self in contmemo:
            ok = vlist is contmemo[self]
            if not ok:
                outgoingvarboxes.append(vlist.ownbox)
            return ok
        if vlist in contmemo:
            assert contmemo[vlist] is not self
            outgoingvarboxes.append(vlist.ownbox)
            return False
        assert self.typedesc is vlist.typedesc
        self_boxes = self.fz_item_boxes
        vlist_boxes = vlist.item_boxes
        if len(self_boxes) != len(vlist_boxes):
            outgoingvarboxes.append(vlist.ownbox)
            return False
        contmemo[self] = vlist
        contmemo[vlist] = self
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(vlist_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        return fullmatch


class VirtualList(AbstractContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        self.item_boxes = []
        # self.ownbox = ...    set in ll_factory

    def enter_block(self, newblock, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.item_boxes:
                box.enter_block(newblock, incoming, memo)

    def force_runtime_container(self, jitstate):
        assert 0

    def freeze(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = FrozenVirtualList(self.typedesc)
            frozens = [box.freeze(memo) for box in self.item_boxes]
            result.fz_item_boxes = frozens
            return result

    def copy(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = VirtualList(self.typedesc)
            result.item_boxes = [box.copy(memo)
                                 for box in self.item_boxes]
            result.ownbox = self.ownbox.copy(memo)
            return result

    def replace(self, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for i in range(len(self.item_boxes)):
                self.item_boxes[i] = self.item_boxes[i].replace(memo)
            self.ownbox = self.ownbox.replace(memo)


def oop_newlist(jitstate, typedesc, lengthbox):
    assert lengthbox.is_constant()
    length = rvalue.ll_getvalue(lengthbox, lltype.Signed)
    assert length == 0
    return typedesc.ll_factory()

def oop_list_append(jitstate, selfbox, itembox):
    assert isinstance(selfbox.content, VirtualList)
    selfbox.content.item_boxes.append(itembox)

def oop_list_getitem(jitstate, selfbox, indexbox):
    assert isinstance(selfbox.content, VirtualList)
    assert indexbox.is_constant()
    index = rvalue.ll_getvalue(indexbox, lltype.Signed)
    return selfbox.content.item_boxes[index]
