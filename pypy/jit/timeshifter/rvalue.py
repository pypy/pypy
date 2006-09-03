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

def exactmatch_memo():
    return Memo()

def copy_memo():
    return Memo()


class RedBox(object):

    def __init__(self, kind, genvar=None):
        self.kind = kind
        self.genvar = genvar    # None or a genvar

    def __repr__(self):
        if not self.genvar:
            return '<dummy>'
        else:
            return '<%r>' % (self.genvar,)

    def is_constant(self):
        return bool(self.genvar) and self.genvar.is_const

    def getgenvar(self, builder):
        return self.genvar

    def enter_block(self, incoming, memo):
        memo = memo.boxes
        if not self.is_constant() and self not in memo:
            incoming.append(self)
            memo[self] = None

    def forcevar(self, builder, memo):
        if self.is_constant():
            # cannot mutate constant boxes in-place
            box = self.copy(memo)
            box.genvar = builder.genop_same_as(self.kind, self.genvar)
            return box
        else:
            # force virtual containers
            self.getgenvar(builder)
            return self

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

def redboxbuilder_void(kind, gv_value):return None
def redboxbuilder_int(kind, gv_value): return IntRedBox(kind, gv_value)
def redboxbuilder_dbl(kind, gv_value): return DoubleRedBox(kind,gv_value)
def redboxbuilder_ptr(kind, gv_value): return PtrRedBox(kind, gv_value)

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

def ll_fromvalue(jitstate, value):
    "Make a constant RedBox from a low-level value."
    rgenop = jitstate.rgenop
    T = lltype.typeOf(value)
    kind = rgenop.kindToken(T)
    gv = rgenop.genconst(value)
    cls = ll_redboxcls(T)
    return cls(kind, gv)

def redbox_from_prebuilt_value(RGenOp, value):
    T = lltype.typeOf(value)
    kind = RGenOp.kindToken(T)
    gv = RGenOp.constPrebuiltGlobal(value)
    cls = ll_redboxcls(T)
    return cls(kind, gv)

def ll_getvalue(box, T):
    "Return the content of a known-to-be-constant RedBox."
    return box.genvar.revealconst(T)


class IntRedBox(RedBox):
    "A red box that contains a constant integer-like value."

    def copy(self, memo):
        memo = memo.boxes
        try:
            return memo[self]
        except KeyError:
            result = memo[self] = IntRedBox(self.kind, self.genvar)
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
            result = memo[self] = DoubleRedBox(self.kind, self.genvar)
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
            result = PtrRedBox(self.kind, self.genvar)
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

    def enter_block(self, incoming, memo):
        if self.content:
            self.content.enter_block(incoming, memo)
        else:
            RedBox.enter_block(self, incoming, memo)

# ____________________________________________________________

class FrozenValue(object):
    """An abstract value frozen in a saved state.
    """


class FrozenIntConst(FrozenValue):

    def __init__(self, gv_const):
        self.gv_const = gv_const

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            self.gv_const.revealconst(lltype.Signed) ==
               box.genvar.revealconst(lltype.Signed)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenIntVar(FrozenValue):

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

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            self.gv_const.revealconst(lltype.Float) ==
               box.genvar.revealconst(lltype.Float)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenDoubleVar(FrozenValue):

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

    def exactmatch(self, box, outgoingvarboxes, memo):
        if (box.is_constant() and
            self.gv_const.revealconst(llmemory.Address) ==
               box.genvar.revealconst(llmemory.Address)):
            return True
        else:
            outgoingvarboxes.append(box)
            return False


class FrozenPtrVar(FrozenValue):

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

    def exactmatch(self, box, outgoingvarboxes, memo):
        assert isinstance(box, PtrRedBox)
        if box.content is None:
            outgoingvarboxes.append(box)
            return False
        else:
            return self.fz_content.exactmatch(box.content, outgoingvarboxes,
                                              memo)
