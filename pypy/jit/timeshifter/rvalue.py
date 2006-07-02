from pypy.rpython import rgenop
from pypy.rpython.lltypesystem import lltype, llmemory

class Memo(object):
    _annspecialcase_ = 'specialize:ctr_location'

    def __init__(self):
        self.boxes = {}
        self.containers = {}

def enter_block_memo():
    return Memo()

def freeze_memo():
    return Memo()

def unfreeze_memo():
    return {} # Memo()

def exactmatch_memo():
    return Memo()

def copy_memo():
    return Memo()


class RedBox(object):

    def __init__(self, gv_type, genvar=rgenop.nullvar):
        assert rgenop.isconst(gv_type)   # temporary?
        self.gv_type = gv_type
        self.genvar = genvar    # nullvar or a genvar

    def __repr__(self):
        if not self.genvar:
            return '<dummy>'
        else:
            return '<%r>' % (rgenop.reveal(self.genvar),)

    def is_constant(self):
        return bool(self.genvar) and rgenop.isconst(self.genvar)

    def getgenvar(self, builder):
        return self.genvar

    def enter_block(self, newblock, incoming, memo):
        memo = memo.boxes
        if not self.is_constant() and self not in memo:
            incoming.append(self.genvar)
            memo[self] = None
            self.genvar = rgenop.geninputarg(newblock, self.gv_type)

    def replace(self, memo):
        memo = memo.boxes
        return memo.setdefault(self, self)


def ll_redboxcls(TYPE):
    if isinstance(TYPE, lltype.Ptr):
        return PtrRedBox
    elif TYPE is lltype.Float:
        return DoubleRedBox
    else:
        assert isinstance(TYPE, lltype.Primitive)
        assert TYPE is not lltype.Void, "cannot make red boxes of voids"
        # XXX what about long longs?
        return IntRedBox

def redboxbuilder_void(gv_type, gv_value):return None
def redboxbuilder_int(gv_ptr, gv_value):  return IntRedBox(gv_ptr, gv_value)
def redboxbuilder_dbl(gv_ptr, gv_value):  return DoubleRedBox(gv_ptr, gv_value)
def redboxbuilder_ptr(gv_ptr, gv_value):  return PtrRedBox(gv_ptr, gv_value)

def ll_redboxbuilder(TYPE):
    if TYPE is lltype.Void:
        return redboxbuilder_void
    elif isinstance(TYPE, lltype.Ptr):
        return redboxbuilder_ptr
    elif TYPE is lltype.Float:
        return redboxbuilder_dbl
    else:
        assert isinstance(TYPE, lltype.Primitive)
        # XXX what about long longs?
        return redboxbuilder_int

def ll_fromvalue(value):
    "Make a constant RedBox from a low-level value."
    T = lltype.typeOf(value)
    gv_type = rgenop.constTYPE(T)
    gv = rgenop.genconst(value)
    cls = ll_redboxcls(T)
    return cls(gv_type, gv)

def ll_getvalue(box, T):
    "Return the content of a known-to-be-constant RedBox."
    return rgenop.revealconst(T, box.genvar)


class IntRedBox(RedBox):
    "A red box that contains a constant integer-like value."

    def copy(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = memo[self] = IntRedBox(self.gv_type, self.genvar)
            return result

    def freeze(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            if self.is_constant():
                result = FrozenIntConst(self.genvar)
            else:
                result = FrozenIntVar()
            memo[self] = result
            return result


class DoubleRedBox(RedBox):
    "A red box that contains a constant double-precision floating point value."

    def copy(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = memo[self] = DoubleRedBox(self.gv_type, self.genvar)
            return result

    def freeze(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            if self.is_constant():
                result = FrozenDoubleConst(self.genvar)
            else:
                result = FrozenDoubleVar()
            memo[self] = result
            return result


class PtrRedBox(RedBox):
    content = None   # or an AbstractContainer

    def __repr__(self):
        if not self.genvar and self.content is not None:
            return '<virtual %s>' % (self.content,)
        else:
            return RedBox.__repr__(self)

    def copy(self, memo):
        boxmemo = memo.boxes
        try:
            return boxmemo[self]
        except KeyError:
            result = PtrRedBox(self.gv_type, self.genvar)
            boxmemo[self] = result
            if self.content:
                result.content = self.content.copy(memo)
            return result

    def replace(self, memo):
        boxmemo = memo.boxes
        try:
            return boxmemo[self]
        except KeyError:
            boxmemo[self] = self
            if self.content:
                self.content.replace(memo)
            return self

    def freeze(self, memo):
        boxmemo = memo.boxes
        try:
            return boxmemo[self]
        except KeyError:
            if self.content:
                result = FrozenPtrVirtual()
                boxmemo[self] = result
                result.fz_content = self.content.freeze(memo)
            else:
                if self.is_constant():
                    result = FrozenPtrConst(self.genvar)
                else:
                    result = FrozenPtrVar()
                boxmemo[self] = result
            return result

    def getgenvar(self, builder):
        if not self.genvar:
            assert self.content
            self.content.force_runtime_container(builder)
            assert self.genvar
        return self.genvar

    def enter_block(self, newblock, incoming, memo):
        if self.content:
            self.content.enter_block(newblock, incoming, memo)
        else:
            RedBox.enter_block(self, newblock, incoming, memo)

# ____________________________________________________________

class FrozenValue(object):
    """An abstract value frozen in a saved state.
    """


class FrozenIntConst(FrozenValue):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            box = memo[self] = IntRedBox(gv_type, self.gv_const)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            rgenop.revealconst(lltype.Signed, self.gv_const) ==
            rgenop.revealconst(lltype.Signed, box.genvar)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenIntVar(FrozenValue):

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            gv_value = rgenop.geninputarg(block, gv_type)
            box = memo[self] = IntRedBox(gv_type, gv_value)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            memo[self] = box
            outgoingvarboxes.append(box)
            return True
        elif memo[self] is box:
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenDoubleConst(FrozenValue):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            box = memo[self] = DoubleRedBox(gv_type, self.gv_const)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            rgenop.revealconst(lltype.Float, self.gv_const) ==
            rgenop.revealconst(lltype.Float, box.genvar)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenDoubleVar(FrozenValue):

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            gv_value = rgenop.geninputarg(block, gv_type)
            box = memo[self] = DoubleRedBox(gv_type, gv_value)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            memo[self] = box
            outgoingvarboxes.append(box)
            return True
        elif memo[self] is box:
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenPtrConst(FrozenValue):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            box = memo[self] = PtrRedBox(gv_type, self.gv_const)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            rgenop.revealconst(llmemory.Address, self.gv_const) ==
            rgenop.revealconst(llmemory.Address, box.genvar)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenPtrVar(FrozenValue):

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            gv_value = rgenop.geninputarg(block, gv_type)
            box = memo[self] = PtrRedBox(gv_type, gv_value)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        memo = memo.boxes
        if self not in memo:
            memo[self] = box
            outgoingvarboxes.append(box)
            return True
        elif memo[self] is box:
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenPtrVirtual(FrozenValue):

    def unfreeze(self, memo, block, gv_type):
        try:
            return memo[self]
        except KeyError:
            box = memo[self] = PtrRedBox(gv_type)
            box.content = self.fz_content.unfreeze(memo, block)
            return box

    def exactmatch(self, box, outgoingvarboxes, memo):
        assert isinstance(box, PtrRedBox)
        if box.content is None:
            outgoingvarboxes.append(box)
            return False
        else:
            return self.fz_content.exactmatch(box.content, outgoingvarboxes,
                                              memo)
