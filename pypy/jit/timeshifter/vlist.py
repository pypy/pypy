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
        self.build_newlist = LIST.list_builder.build_newlist
        self.build_setitem = LIST.list_builder.build_setitem

    def factory(self, length, itembox):
        vlist = VirtualList(self, length, itembox)
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

    def __init__(self, typedesc, length=0, itembox=None):
        self.typedesc = typedesc
        self.item_boxes = [itembox] * length
        # self.ownbox = ...    set in factory()

    def enter_block(self, newblock, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.item_boxes:
                box.enter_block(newblock, incoming, memo)

    def force_runtime_container(self, builder):
        typedesc = self.typedesc
        boxes = self.item_boxes
        self.item_boxes = None
        gv_list = typedesc.build_newlist(builder, len(boxes))
        self.ownbox.genvar = gv_list
        self.ownbox.content = None
        for i in range(len(boxes)):
            gv_item = boxes[i].getgenvar(builder)
            typedesc.build_setitem(builder, gv_list, i, gv_item)

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


def oop_newlist(jitstate, oopspecdesc, lengthbox, itembox=None):
    if lengthbox.is_constant():
        length = rvalue.ll_getvalue(lengthbox, lltype.Signed)
        if length == 0 or itembox is not None:
            return oopspecdesc.typedesc.factory(length, itembox)
    return oopspecdesc.residual_call(jitstate.curbuilder, [lengthbox, itembox])

def oop_list_append(jitstate, oopspecdesc, selfbox, itembox):
    if isinstance(selfbox.content, VirtualList):
        selfbox.content.item_boxes.append(itembox)
    else:
        oopspecdesc.residual_call(jitstate.curbuilder, [selfbox, itembox])

def oop_list_getitem(jitstate, oopspecdesc, selfbox, indexbox):
    if isinstance(selfbox.content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        return selfbox.content.item_boxes[index]
    else:
        return oopspecdesc.residual_call(jitstate.curbuilder, [selfbox, indexbox])

def oop_list_setitem(jitstate, oopspecdesc, selfbox, indexbox, itembox):
    if isinstance(selfbox.content, VirtualList) and indexbox.is_constant():
        index = rvalue.ll_getvalue(indexbox, lltype.Signed)
        selfbox.content.item_boxes[index] = itembox
    else:
        oopspecdesc.residual_call(jitstate.curbuilder, [selfbox, indexbox, itembox])
