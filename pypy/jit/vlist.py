from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rtyper import LowLevelOpList
from pypy.jit.llvalue import LLAbstractValue, AConstant, ll_dummy_value
from pypy.jit.llcontainer import LLAbstractContainer


class LLVirtualList(LLAbstractContainer):
    type_name = 'list'

    def __init__(self, T, items_a=None):
        self.T = T
        if items_a is None:
            self.items_a = []
        else:
            self.items_a = items_a

    def flatten(self, memo):
        assert self not in memo.seen; memo.seen[self] = True  # debugging only
        for a_value in self.items_a:
            a_value.flatten(memo)

    def match(self, live, memo):
        if self.__class__ is not live.__class__:
            return False
        if len(self.items_a) != len(live.items_a):
            return False
        for a1, a2 in zip(self.items_a, live.items_a):
            if not a1.match(a2, memo):
                return False
        else:
            return True

    def freeze(self, memo):
        items_a = [a.freeze(memo) for a in self.items_a]
        return LLVirtualList(self.T, items_a)

    def unfreeze(self, memo, block):
        items_a = [a.unfreeze(memo, block) for a in self.items_a]
        return LLVirtualList(self.T, items_a)

    def build_runtime_container(self, builder):
        items_v = [a.forcegenvarorconst(builder) for a in self.items_a]
        v_result = self.T.list_builder(builder, items_v)
        return v_result

    # ____________________________________________________________
    # High-level operations

    def oop_len(self, op):
        return LLAbstractValue(AConstant(len(self.items_a)))

    def oop_nonzero(self, op):
        return LLAbstractValue(AConstant(bool(self.items_a)))

    def oop_getitem(self, op, a_index):
        c_index = a_index.maybe_get_constant()
        if c_index is None:
            raise NotImplementedError
        return self.items_a[c_index.value]

    def oop_setitem(self, op, a_index, a_newobj):
        c_index = a_index.maybe_get_constant()
        if c_index is None:
            raise NotImplementedError
        self.items_a[c_index.value] = a_newobj

    def oop_delitem(self, op, a_index):
        c_index = a_index.maybe_get_constant()
        if c_index is None:
            raise NotImplementedError
        del self.items_a[c_index.value]

    def oop_append(self, op, a_newobj):
        self.items_a.append(a_newobj)

    def oop_insert(self, op, a_index, a_newobj):
        c_index = a_index.maybe_get_constant()
        if c_index is None:
            raise NotImplementedError
        self.items_a.insert(c_index.value, a_newobj)

    def oop_pop(self, op, a_index=None):
        if a_index is None:
            return self.items_a.pop()
        else:
            c_index = a_index.maybe_get_constant()
            if c_index is None:
                raise NotImplementedError
            return self.items_a.pop(c_index.value)

    def oop_reverse(self, op):
        self.items_a.reverse()

    def oop_copy(self, op):
        items_a = list(self.items_a)
        LIST = op.result.concretetype.TO
        virtuallist = LLVirtualList(LIST, items_a)
        return LLAbstractValue(content=virtuallist)

    def oop_concat(self, op, a_other):
        if not isinstance(a_other.content, LLVirtualList):
            raise NotImplementedError
        items_a = self.items_a + a_other.content.items_a
        LIST = op.result.concretetype.TO
        virtuallist = LLVirtualList(LIST, items_a)
        return LLAbstractValue(content=virtuallist)


def oop_newlist(op, a_numitems, a_item=ll_dummy_value):
    c_numitems = a_numitems.maybe_get_constant()
    if c_numitems is None:
        raise NotImplementedError
    LIST = op.result.concretetype.TO
    items_a = [a_item] * c_numitems.value
    virtuallist = LLVirtualList(LIST, items_a)
    return LLAbstractValue(content=virtuallist)
