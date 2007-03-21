import operator
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem import rdict
from pypy.jit.timeshifter.rcontainer import VirtualContainer, FrozenContainer
from pypy.jit.timeshifter.rcontainer import cachedtype
from pypy.jit.timeshifter import rvalue
from pypy.rlib.objectmodel import r_dict

HASH = lltype.Signed

# XXXXXXXXXX! ARGH.
# cannot use a dictionary as the item_boxes at all, because of order issues


class LLEqDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, KEY, keyeq, keyhash):
        # this makes one version of the following function per KEY,
        # which is supposed to be the ll type of x and y

        def lleq(x, y):
            return keyeq(x, y)
        def llhash(x):
            return keyhash(x)

        class VirtualDict(AbstractVirtualDict):

            def make_item_boxes(self):
                self.item_boxes = r_dict(lleq, llhash)

            def getboxes(self):
                return self.item_boxes.values()

            def getitems_and_makeempty(self, rgenop):
                result = [(rgenop.genconst(key), box, llhash(key))
                          for key, box in self.item_boxes.iteritems()]
                self.item_boxes = None
                return result

            def getitem(self, keybox):
                key = rvalue.ll_getvalue(keybox, KEY)
                return self.item_boxes[key]

            def setitem(self, keybox, valuebox):
                key = rvalue.ll_getvalue(keybox, KEY)
                self.item_boxes[key] = valuebox

            def copy_from(self, other, memo):
                assert isinstance(other, VirtualDict)
                self.make_item_boxes()
                for key, valuebox in other.item_boxes.iteritems():
                    self.item_boxes[key] = valuebox.copy(memo)

            def internal_replace(self, memo):
                changes = []
                for key, valuebox in self.item_boxes.iteritems():
                    newbox = valuebox.replace(memo)
                    if newbox is not valuebox:
                        changes.append((key, newbox))
                for key, newbox in changes:
                    self.item_boxes[key] = newbox


        class FrozenVirtualDict(AbstractFrozenVirtualDict):

            def freeze_from(self, vdict, memo):
                assert isinstance(vdict, VirtualDict)
                frozens = []
                for key, valuebox in vdict.item_boxes.iteritems():
                    frozens.append((key, valuebox.freeze(memo)))
                self.fz_item_boxes = frozens

            def same_keys_as(self, vdict, boxes):
                assert isinstance(vdict, VirtualDict)
                self_boxes = self.fz_item_boxes
                vdict_boxes = vdict.item_boxes
                if len(self_boxes) != len(vdict_boxes):
                    return False
                for key, selfbox in self_boxes:
                    try:
                        vdictbox = vdict_boxes[key]
                    except KeyError:
                        return False
                    boxes.append((selfbox, vdictbox))
                return True


        self.VirtualDict = VirtualDict
        self.FrozenVirtualDict = FrozenVirtualDict

        VirtualDict.FrozenVirtualDict = FrozenVirtualDict


class DictTypeDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, hrtyper, DICT):
        RGenOp = hrtyper.RGenOp
        rtyper = hrtyper.rtyper
        bk = rtyper.annotator.bookkeeper
        self.DICT = DICT
        self.DICTPTR = lltype.Ptr(DICT)
        self.ptrkind = RGenOp.kindToken(self.DICTPTR)

        argtypes = [bk.immutablevalue(DICT)]
        ll_newdict_ptr = rtyper.annotate_helper_fn(rdict.ll_newdict,
                                                   argtypes)
        self.gv_ll_newdict = RGenOp.constPrebuiltGlobal(ll_newdict_ptr)
        self.tok_ll_newdict = RGenOp.sigToken(lltype.typeOf(ll_newdict_ptr).TO)

        argtypes = [self.DICTPTR, DICT.KEY, DICT.VALUE, HASH]
        ll_insertclean = rtyper.annotate_helper_fn(rdict.ll_dict_insertclean,
                                                    argtypes)
        self.gv_ll_insertclean = RGenOp.constPrebuiltGlobal(ll_insertclean)
        self.tok_ll_insertclean = RGenOp.sigToken(
            lltype.typeOf(ll_insertclean).TO)

        # XXX some fishing that only works if the DICT does not come from
        # an r_dict
        if DICT.keyeq is None:
            keyeq = operator.eq
        else:
            assert isinstance(DICT.keyeq, lltype.staticAdtMethod)
            keyeq = DICT.keyeq.__get__(42)
        assert isinstance(DICT.keyhash, lltype.staticAdtMethod)
        keyhash = DICT.keyhash.__get__(42)
        keydesc = LLEqDesc(DICT.KEY, keyeq, keyhash)
        self.VirtualDict = keydesc.VirtualDict

    def _freeze_(self):
        return True

    def factory(self):
        vdict = self.VirtualDict(self)
        box = rvalue.PtrRedBox(self.ptrkind, known_nonzero=True)
        box.content = vdict
        vdict.ownbox = box
        return box

TypeDesc = DictTypeDesc


class AbstractFrozenVirtualDict(FrozenContainer):
    _attrs_ = ('typedesc',)

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_item_boxes initialized later

    def exactmatch(self, vdict, outgoingvarboxes, memo):
        assert isinstance(vdict, AbstractVirtualDict)
        contmemo = memo.containers
        if self in contmemo:
            ok = vdict is contmemo[self]
            if not ok:
                outgoingvarboxes.append(vdict.ownbox)
            return ok
        if vdict in contmemo:
            assert contmemo[vdict] is not self
            outgoingvarboxes.append(vdict.ownbox)
            return False
        assert self.typedesc is vdict.typedesc
        boxes = []
        if not self.same_keys_as(vdict, boxes):
            outgoingvarboxes.append(vdict.ownbox)
            return False
        contmemo[self] = vdict
        contmemo[vdict] = self
        fullmatch = True
        for selfbox, vdictbox in boxes:
            if not selfbox.exactmatch(vdictbox,
                                      outgoingvarboxes,
                                      memo):
                fullmatch = False
        return fullmatch

    def freeze_from(self, vdict, memo):
        raise NotImplementedError

    def same_keys_as(self, vdict, boxes):
        raise NotImplementedError


class AbstractVirtualDict(VirtualContainer):
    _attrs_ = ('typedesc',)     # and no item_boxes

    FrozenVirtualDict = AbstractFrozenVirtualDict    # overridden in subclasses

    def __init__(self, typedesc):
        self.typedesc = typedesc
        self.make_item_boxes()
        # self.ownbox = ...    set in factory()

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.getboxes():
                box.enter_block(incoming, memo)

    def force_runtime_container(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        items = self.getitems_and_makeempty(builder.rgenop)

        args_gv = []
        gv_dict = builder.genop_call(typedesc.tok_ll_newdict,
                                     typedesc.gv_ll_newdict,
                                     args_gv)
        self.ownbox.setgenvar_hint(gv_dict, known_nonzero=True)
        self.ownbox.content = None
        for gv_key, valuebox, hash in items:
            gv_hash = builder.rgenop.genconst(hash)
            gv_value = valuebox.getgenvar(jitstate)
            args_gv = [gv_dict, gv_key, gv_value, gv_hash]
            builder.genop_call(typedesc.tok_ll_insertclean,
                               typedesc.gv_ll_insertclean,
                               args_gv)

    def freeze(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = self.FrozenVirtualDict(self.typedesc)
            result.freeze_from(self, memo)
            return result

    def copy(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = self.__class__(self.typedesc)
            result.copy_from(self, memo)
            result.ownbox = self.ownbox.copy(memo)
            return result

    def replace(self, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            self.internal_replace(memo)
            self.ownbox = self.ownbox.replace(memo)

    def make_item_boxes(self):
        raise NotImplementedError

    def getboxes(self):
        raise NotImplementedError

    def getitems_and_makeempty(self, rgenop):
        raise NotImplementedError

    def getitem(self, keybox):
        raise NotImplementedError

    def setitem(self, keybox, valuebox):
        raise NotImplementedError

    def copy_from(self, other, memo):
        raise NotImplementedError

    def internal_replace(self, memo):
        raise NotImplementedError


def oop_newdict(jitstate, oopspecdesc):
    return oopspecdesc.typedesc.factory()

def oop_dict_setitem(jitstate, oopspecdesc, selfbox, keybox, valuebox):
    content = selfbox.content
    if isinstance(content, AbstractVirtualDict) and keybox.is_constant():
        content.setitem(keybox, valuebox)
    else:
        oopspecdesc.residual_call(jitstate, [selfbox, keybox, valuebox])

def oop_dict_getitem(jitstate, oopspecdesc, deepfrozen, selfbox, keybox):
    content = selfbox.content
    if isinstance(content, AbstractVirtualDict) and keybox.is_constant():
        try:
            return content.getitem(keybox)
        except KeyError:
            return oopspecdesc.residual_exception(jitstate, KeyError)
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox, keybox],
                                         deepfrozen=deepfrozen)
oop_dict_getitem.couldfold = True

def oop_dict_contains(jitstate, oopspecdesc, deepfrozen, selfbox, keybox):
    content = selfbox.content
    if isinstance(content, AbstractVirtualDict) and keybox.is_constant():
        try:
            content.getitem(keybox)
            res = True
        except KeyError:
            res = False
        return rvalue.ll_fromvalue(jitstate, res)
    else:
        return oopspecdesc.residual_call(jitstate, [selfbox, keybox],
                                         deepfrozen=deepfrozen)
oop_dict_contains.couldfold = True
