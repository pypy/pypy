from pypy.annotation.listdef import ListItem
from pypy.jit.hintannotator.model import SomeLLAbstractConstant
from pypy.jit.hintannotator.model import SomeLLAbstractContainer, reorigin
from pypy.jit.hintannotator.bookkeeper import getbookkeeper
from pypy.jit.hintannotator.container import AbstractContainerDef
from pypy.jit.hintannotator.container import make_item_annotation
from pypy.rpython.lltypesystem import lltype

class VirtualListDef(AbstractContainerDef):
    type_name = 'list'

    def __init__(self, bookkeeper, LIST):
        AbstractContainerDef.__init__(self, bookkeeper, LIST)
        hs = make_item_annotation(bookkeeper, LIST.ITEM)
        self.listitem = ListItem(bookkeeper, hs)
        self.listitem.itemof[self] = True

    def read_item(self):
        self.listitem.read_locations[self.bookkeeper.position_key] = True
        return self.listitem.s_value

    def same_as(self, other):
        return self.listitem == other.listitem

    def union(self, other):
        assert self.T == other.T
        self.listitem.merge(other.listitem)
        return self

    def generalize_item(self, hs_value):
        assert hs_value.concretetype == self.T.ITEM
        self.listitem.generalize(hs_value)

    # ________________________________________
    # OOP high-level operations

    def oop_len(self):
        origin = getbookkeeper().myorigin()
        return SomeLLAbstractConstant(lltype.Signed, {origin: True})

    def oop_nonzero(self):
        origin = getbookkeeper().myorigin()
        return SomeLLAbstractConstant(lltype.Bool, {origin: True})

    def oop_getitem(self, hs_index):
        assert hs_index.concretetype == lltype.Signed
        hs_res = self.read_item()
        return reorigin(hs_res, hs_res, hs_index)

    def oop_setitem(self, hs_index, hs_value):
        assert hs_index.concretetype == lltype.Signed
        self.generalize_item(hs_value)

    def oop_delitem(self, hs_index):
        assert hs_index.concretetype == lltype.Signed

    def oop_append(self, hs_value):
        self.generalize_item(hs_value)

    def oop_insert(self, hs_index, hs_value):
        assert hs_index.concretetype == lltype.Signed
        self.generalize_item(hs_value)

    def oop_pop(self, hs_index=None):
        assert hs_index is None or hs_index.concretetype == lltype.Signed
        hs_res = self.read_item()
        return reorigin(hs_res, hs_res, hs_index)

    def oop_reverse(self):
        pass

    def oop_copy(self):
        bk = self.bookkeeper
        vlistdef = bk.getvirtualcontainerdef(self.T, VirtualListDef)
        vlistdef.generalize_item(self.read_item())
        return SomeLLAbstractContainer(vlistdef)

    def oop_concat(self, hs_other):
        assert isinstance(hs_other, SomeLLAbstractContainer) # for now
        assert hs_other.contentdef.T == self.T
        return self.oop_copy()

# ____________________________________________________________

def oop_newlist(hs_numitems, hs_item=None):
    bk = getbookkeeper()
    LIST = bk.current_op_concretetype().TO
    vlistdef = bk.getvirtualcontainerdef(LIST, VirtualListDef)
    return SomeLLAbstractContainer(vlistdef)
