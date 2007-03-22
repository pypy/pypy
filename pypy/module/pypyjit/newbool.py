from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cachedtype
from pypy.annotation import model as annmodel
from pypy.jit.timeshifter import rvalue, rcontainer
from pypy.objspace.std.boolobject import W_BoolObject


class NewBoolDesc:
    __metaclass__ = cachedtype

    def __init__(self, hrtyper):
        self.hrtyper = hrtyper
        RGenOp = hrtyper.RGenOp
        rtyper = hrtyper.rtyper
        bk = rtyper.annotator.bookkeeper
        s_w_bool = annmodel.unionof(bk.immutablevalue(W_BoolObject.w_False),
                                    bk.immutablevalue(W_BoolObject.w_True))
        r_w_bool = rtyper.getrepr(s_w_bool)
        self.ll_False = r_w_bool.convert_const(W_BoolObject.w_False)
        self.ll_True  = r_w_bool.convert_const(W_BoolObject.w_True)

        A = lltype.Array(lltype.typeOf(self.ll_False))
        self.ll_bools = lltype.malloc(A, 2, immortal=True)
        self.ll_bools[0] = self.ll_False
        self.ll_bools[1] = self.ll_True
        self.gv_bools = RGenOp.constPrebuiltGlobal(self.ll_bools)
        self.boolsToken = RGenOp.arrayToken(A)

        self.bools_gv = [RGenOp.constPrebuiltGlobal(self.ll_False),
                         RGenOp.constPrebuiltGlobal(self.ll_True)]

        self.ptrkind = RGenOp.kindToken(r_w_bool.lowleveltype)
        self.boolkind = RGenOp.kindToken(lltype.Bool)

        ll_BoolObject = r_w_bool.rclass.getvtable()
        self.BoolObjectBox = rvalue.redbox_from_prebuilt_value(RGenOp,
                                                               ll_BoolObject)

        self.Falsebox = rvalue.redbox_from_prebuilt_value(RGenOp, False)
        self.Truebox = rvalue.redbox_from_prebuilt_value(RGenOp, True)
        self.boolboxes = [self.Falsebox, self.Truebox]

    def _freeze_(self):
        return True

    def vboolfactory(self):
        vbool = VirtualBool(self)
        box = rvalue.PtrRedBox(self.ptrkind, known_nonzero=True)
        box.content = vbool
        vbool.ownbox = box
        return vbool

    def metafunc(self, jitstate, spacevoid, valuebox):
        vbool = self.vboolfactory()
        vbool.valuebox = valuebox
        return vbool.ownbox

    def getboolbox(self, jitstate, gv_bool, reverse=False):
        if gv_bool.is_const:
            flag = gv_bool.revealconst(lltype.Bool)
            return self.boolboxes[flag ^ reverse]
        else:
            if reverse:
                gv_bool = jitstate.curbuilder.genop1("bool_not", gv_bool)
            return rvalue.IntRedBox(self.boolkind, gv_bool)

    def genbooleq(self, jitstate, gv_bool1, gv_bool2, reverse=False):
        if gv_bool1.is_const:
            reverse ^= not gv_bool1.revealconst(lltype.Bool)
            return self.getboolbox(jitstate, gv_bool2, reverse)
        elif gv_bool2.is_const:
            reverse ^= not gv_bool2.revealconst(lltype.Bool)
            return self.getboolbox(jitstate, gv_bool1, reverse)
        else:
            # XXX maybe gv_bool1 == gv_bool2 :-)
            curbuilder = jitstate.curbuilder
            gv_int1 = curbuilder.genop1("cast_bool_to_int", gv_bool1)
            gv_int2 = curbuilder.genop1("cast_bool_to_int", gv_bool2)
            if reverse:
                gv_res = curbuilder.genop2("int_ne", gv_int1, gv_int2)
            else:
                gv_res = curbuilder.genop2("int_eq", gv_int1, gv_int2)
            return rvalue.IntRedBox(self.boolkind, gv_res)


class VirtualBool(rcontainer.VirtualContainer):

    def __init__(self, newbooldesc):
        self.newbooldesc = newbooldesc
        #self.valuebox = ... set independently

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            self.valuebox.enter_block(incoming, memo)

    def force_runtime_container(self, jitstate):
        desc = self.newbooldesc
        valuebox = self.valuebox
        if valuebox.is_constant():
            value = valuebox.genvar.revealconst(lltype.Bool)
            genvar = desc.bools_gv[value]
        else:
            gv_index = valuebox.getgenvar(jitstate)
            gv_index = jitstate.curbuilder.genop1("cast_bool_to_int", gv_index)
            genvar = jitstate.curbuilder.genop_getarrayitem(
                desc.boolsToken,
                desc.gv_bools,
                gv_index)
        self.ownbox.setgenvar_hint(genvar, known_nonzero=True)
        self.ownbox.content = None

    def freeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = FrozenBool(self.newbooldesc)
        frozenbox = self.valuebox.freeze(memo)
        result.fz_valuebox = frozenbox
        return result

    def copy(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = VirtualBool(self.newbooldesc)
        result.valuebox = self.valuebox.copy(memo)
        result.ownbox = self.ownbox.copy(memo)
        return result

    def replace(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        contmemo[self] = None
        self.valuebox = self.valuebox.replace(memo)
        self.ownbox = self.ownbox.replace(memo)

    def op_getfield(self, jitstate, fielddesc):
        if fielddesc.fieldindex == 0:     # the __class__ field
            return self.newbooldesc.BoolObjectBox
        else:
            # assume it is the 'boolval' field
            return self.valuebox

    def op_ptreq(self, jitstate, otherbox, reverse):
        desc = self.newbooldesc
        if otherbox.is_constant():
            addr = otherbox.genvar.revealconst(llmemory.Address)
            if addr == llmemory.cast_ptr_to_adr(desc.ll_False):
                return desc.getboolbox(jitstate, self.valuebox.genvar,
                                       not reverse)
            elif addr == llmemory.cast_ptr_to_adr(desc.ll_True):
                return desc.getboolbox(jitstate, self.valuebox.genvar,
                                       reverse)
            else:
                return desc.boolboxes[False ^ reverse]

        othercontent = otherbox.content
        if not isinstance(othercontent, VirtualBool):
            return None     # no clue

        return desc.genbooleq(jitstate,
                              self.valuebox.genvar,
                              othercontent.valuebox.genvar,
                              reverse)


class FrozenBool(rcontainer.FrozenContainer):

    def __init__(self, newbooldesc):
        self.newbooldesc = newbooldesc
        #self.fz_valuebox initialized later

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        # XXX code duplication with rcontainer...
        assert isinstance(vstruct, rcontainer.VirtualContainer)
        contmemo = memo.containers
        if self in contmemo:
            ok = vstruct is contmemo[self]
            if not ok:
                outgoingvarboxes.append(vstruct.ownbox)
            return ok
        if vstruct in contmemo:
            assert contmemo[vstruct] is not self
            outgoingvarboxes.append(vstruct.ownbox)
            return False
        if not isinstance(vstruct, VirtualBool):
            if not memo.force_merge:
                raise rvalue.DontMerge
            outgoingvarboxes.append(vstruct.ownbox)
            return False
        contmemo[self] = vstruct
        contmemo[vstruct] = self
        return self.fz_valuebox.exactmatch(vstruct.valuebox,
                                           outgoingvarboxes,
                                           memo)

    def unfreeze(self, incomingvarboxes, memo):
        contmemo = memo.containers
        if self in contmemo:
            return contmemo[self]
        vbool = self.newbooldesc.vboolfactory()
        ownbox = vbool.ownbox
        contmemo[self] = ownbox
        vbool.valuebox = self.fz_valuebox.unfreeze(incomingvarboxes, memo)
        return ownbox
