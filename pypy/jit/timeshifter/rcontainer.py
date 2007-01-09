
import operator
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.annlowlevel import cachedtype
from pypy.jit.timeshifter import rvalue
from pypy.rlib.unroll import unrolling_iterable

from pypy.rpython.lltypesystem import lloperation
debug_print = lloperation.llop.debug_print
debug_pdb = lloperation.llop.debug_pdb

class AbstractContainer(object):
    __slots__ = []

    def op_getfield(self, jitstate, fielddesc):
        raise NotImplementedError

    def op_setfield(self, jitstate, fielddesc, valuebox):
        raise NotImplementedError

    def op_getsubstruct(self, jitstate, fielddesc):
        raise NotImplementedError


class VirtualContainer(AbstractContainer):
    __slots__ = []


class FrozenContainer(AbstractContainer):
    __slots__ = []

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        raise NotImplementedError
    
    def unfreeze(self, incomingvarboxes, memo):
        raise NotImplementedError

# ____________________________________________________________

class StructTypeDesc(object):
    __metaclass__ = cachedtype
    firstsubstructdesc = None
    arrayfielddesc = None
    alloctoken = None
    varsizealloctoken = None
    materialize = None        
    
    def __init__(self, RGenOp, TYPE):
        self.TYPE = TYPE
        self.PTRTYPE = lltype.Ptr(TYPE)
        self.ptrkind = RGenOp.kindToken(self.PTRTYPE)
        innermostdesc = self
        if not TYPE._is_varsize():
            self.alloctoken = RGenOp.allocToken(TYPE)
        fielddescs = []
        fielddesc_by_name = {}
        for name in self.TYPE._names:
            FIELDTYPE = getattr(self.TYPE, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                if isinstance(FIELDTYPE, lltype.Array):
                    self.arrayfielddesc = ArrayFieldDesc(RGenOp, FIELDTYPE)
                    self.varsizealloctoken = RGenOp.varsizeAllocToken(TYPE)
                    continue
                substructdesc = StructTypeDesc(RGenOp, FIELDTYPE)
                assert name == self.TYPE._names[0], (
                    "unsupported: inlined substructures not as first field")
                fielddescs.extend(substructdesc.fielddescs)
                self.firstsubstructdesc = substructdesc
                innermostdesc = substructdesc.innermostdesc
            else:
                index = len(fielddescs)
                if FIELDTYPE is lltype.Void:
                    desc = None
                else:
                    desc = StructFieldDesc(RGenOp, self.PTRTYPE, name, index)
                    fielddescs.append(desc)
                fielddesc_by_name[name] = desc
        self.fielddescs = fielddescs
        self.fielddesc_by_name = fielddesc_by_name
        self.innermostdesc = innermostdesc

        self.immutable = TYPE._hints.get('immutable', False)
        self.noidentity = TYPE._hints.get('noidentity', False)

        if TYPE._hints.get('virtualizable', False):
            self.__class__ = VirtualizableStructTypeDesc
            self.VStructCls = VirtualizableStruct
            outside_null = self.PTRTYPE._defl()
            self.gv_defl_outside = RGenOp.constPrebuiltGlobal(outside_null)
        else:
            self.VStructCls = VirtualStruct
            
        if self.immutable and self.noidentity:
            descs = unrolling_iterable(fielddescs)
            def materialize(rgenop, boxes):
                s = lltype.malloc(TYPE)
                i = 0
                for desc in descs:
                    v = rvalue.ll_getvalue(boxes[i], desc.RESTYPE)
                    setattr(s, desc.fieldname, v)
                    i = i + 1
                return rgenop.genconst(s)

            self.materialize = materialize
                
    def getfielddesc(self, name):
        return self.fielddesc_by_name[name]

    def factory(self):
        vstruct = VirtualStruct(self)
        vstruct.content_boxes = [desc.redboxcls(desc.kind, desc.gv_default)
                                 for desc in self.fielddescs]
        box = rvalue.PtrRedBox(self.innermostdesc.ptrkind)
        box.content = vstruct
        vstruct.ownbox = box
        return box

    def ll_factory(self):
        # interface for rtyper.py, specialized for each 'self'
        return self.factory()

    def _freeze_(self):
        return True

    def compact_repr(self): # goes in ll helper names
        return "Desc_%s" % (self.TYPE._short_name(),)

class VirtualizableStructTypeDesc(StructTypeDesc):
    
    def factory(self):
        vstruct = VirtualizableStruct(self)
        vstruct.content_boxes = [desc.redboxcls(desc.kind, desc.gv_default)
                                 for desc in self.fielddescs]
        outsidebox = rvalue.PtrRedBox(self.innermostdesc.ptrkind,
                                      self.gv_defl_outside)
        vstruct.content_boxes.append(outsidebox)
        box = rvalue.PtrRedBox(self.innermostdesc.ptrkind)
        box.content = vstruct
        vstruct.ownbox = box
        return box
    
# XXX basic field descs for now
class FieldDesc(object):
    __metaclass__ = cachedtype
    allow_void = False

    def __init__(self, RGenOp, PTRTYPE, RESTYPE):
        self.PTRTYPE = PTRTYPE
        if isinstance(RESTYPE, lltype.ContainerType):
            RESTYPE = lltype.Ptr(RESTYPE)
        self.RESTYPE = RESTYPE
        self.ptrkind = RGenOp.kindToken(PTRTYPE)
        self.kind = RGenOp.kindToken(RESTYPE)
        if RESTYPE is lltype.Void and self.allow_void:
            pass   # no redboxcls at all
        else:
            self.redboxcls = rvalue.ll_redboxcls(RESTYPE)
        self.immutable = PTRTYPE.TO._hints.get('immutable', False)

    def _freeze_(self):
        return True

class NamedFieldDesc(FieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name):
        FieldDesc.__init__(self, RGenOp, PTRTYPE, getattr(PTRTYPE.TO, name))
        T = self.PTRTYPE.TO
        self.fieldname = name
        self.fieldtoken = RGenOp.fieldToken(T, name)

    def compact_repr(self): # goes in ll helper names
        return "Fld_%s_in_%s" % (self.fieldname, self.PTRTYPE._short_name())

    def generate_get(self, builder, genvar):
        gv_item = builder.genop_getfield(self.fieldtoken, genvar)
        return self.redboxcls(self.kind, gv_item)

    def generate_set(self, builder, genvar, box):
        builder.genop_setfield(self.fieldtoken, genvar, box.getgenvar(builder))

    def generate_getsubstruct(self, builder, genvar):
        gv_sub = builder.genop_getsubstruct(self.fieldtoken, genvar)
        return self.redboxcls(self.kind, gv_sub)

class StructFieldDesc(NamedFieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name, index):
        NamedFieldDesc.__init__(self, RGenOp, PTRTYPE, name)
        self.fieldindex = index
        self.gv_default = RGenOp.constPrebuiltGlobal(self.RESTYPE._defl())
        self.defaultbox = self.redboxcls(self.kind, self.gv_default)

class ArrayFieldDesc(FieldDesc):
    allow_void = True

    def __init__(self, RGenOp, TYPE):
        assert isinstance(TYPE, lltype.Array)
        FieldDesc.__init__(self, RGenOp, lltype.Ptr(TYPE), TYPE.OF)
        self.arraytoken = RGenOp.arrayToken(TYPE)
        self.varsizealloctoken = RGenOp.varsizeAllocToken(TYPE)
        self.indexkind = RGenOp.kindToken(lltype.Signed)

# ____________________________________________________________

class FrozenVirtualStruct(FrozenContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_content_boxes initialized later

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        assert isinstance(vstruct, VirtualStruct)
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
        if self.typedesc is not vstruct.typedesc:
            if not memo.force_merge:
                raise rvalue.DontMerge
            outgoingvarboxes.append(vstruct.ownbox)
            return False
        contmemo[self] = vstruct
        contmemo[vstruct] = self
        self_boxes = self.fz_content_boxes
        vstruct_boxes = vstruct.content_boxes
        fullmatch = True
        for i in range(len(self_boxes)):
            if not self_boxes[i].exactmatch(vstruct_boxes[i],
                                            outgoingvarboxes,
                                            memo):
                fullmatch = False
        return fullmatch

    def unfreeze(self, incomingvarboxes, memo):
        contmemo = memo.containers
        if self in contmemo:
            return contmemo[self]
        typedesc = self.typedesc
        ownbox = typedesc.factory()
        contmemo[self] = ownbox
        vstruct = ownbox.content
        assert isinstance(vstruct, VirtualStruct)
        self_boxes = self.fz_content_boxes
        for i in range(len(self_boxes)):
            fz_box = self_boxes[i]
            vstruct.content_boxes[i] = fz_box.unfreeze(incomingvarboxes,
                                                       memo)
        return ownbox


class VirtualStruct(VirtualContainer):
    typedesc = None

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.content_boxes = ... set in factory()
        #self.ownbox = ... set in factory()

    def enter_block(self, incoming, memo):
        assert self.typedesc is not None
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.content_boxes:
                box.enter_block(incoming, memo)

    def force_runtime_container(self, builder):
        typedesc = self.typedesc
        assert typedesc is not None
        boxes = self.content_boxes
        self.content_boxes = None
        if typedesc.materialize is not None:
            for box in boxes:
                if box is None or not box.is_constant():
                    break
            else:
                gv = typedesc.materialize(builder.rgenop, boxes)
                self.ownbox.genvar = gv
                self.ownbox.content = None
                return
        debug_print(lltype.Void, "FORCE CONTAINER")
        #debug_pdb(lltype.Void)
        genvar = builder.genop_malloc_fixedsize(typedesc.alloctoken)
        # force the box pointing to this VirtualStruct
        self.ownbox.genvar = genvar
        self.ownbox.content = None
        fielddescs = typedesc.fielddescs
        for i in range(len(fielddescs)):
            fielddesc = fielddescs[i]
            box = boxes[i]
            fielddesc.generate_set(builder, genvar, box)

    def freeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        assert self.typedesc is not None
        result = contmemo[self] = FrozenVirtualStruct(self.typedesc)
        frozens = [box.freeze(memo) for box in self.content_boxes]
        result.fz_content_boxes = frozens
        return result

    def copy(self, memo):
        typedesc = self.typedesc
        assert typedesc is not None
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = typedesc.VStructCls(typedesc)
        result.content_boxes = [box.copy(memo)
                                for box in self.content_boxes]
        result.ownbox = self.ownbox.copy(memo)
        return result

    def replace(self, memo):
        assert self.typedesc is not None        
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        contmemo[self] = None
        content_boxes = self.content_boxes
        for i in range(len(content_boxes)):
            content_boxes[i] = content_boxes[i].replace(memo)
        self.ownbox = self.ownbox.replace(memo)

    def op_getfield(self, jitstate, fielddesc):
        return self.content_boxes[fielddesc.fieldindex]

    def op_setfield(self, jitstate, fielddesc, valuebox):
        self.content_boxes[fielddesc.fieldindex] = valuebox

    def op_getsubstruct(self, jitstate, fielddesc):
        return self.ownbox

class VirtualizableStruct(VirtualStruct):

    def force_runtime_container(self, builder):
        assert 0

    def getgenvar(self, builder):
        typedesc = self.typedesc
        assert typedesc is not None
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_defl_outside:
            gv_outside = builder.genop_malloc_fixedsize(typedesc.alloctoken)
            self.content_boxes[-1].genvar = gv_outside
            # xxx jitstate please
        return gv_outside

    def store_back(self, builder):
        fielddescs = self.typedesc.fielddescs
        boxes = self.content_boxes
        gv_outside = boxes[-1].genvar
        for i in range(1, len(fielddescs)):
            fielddesc = fielddescs[i]
            box = boxes[i]
            fielddesc.generate_set(builder, gv_outside, box)

# ____________________________________________________________

class FrozenPartialDataStruct(AbstractContainer):

    def __init__(self):
        self.fz_data = []

    def getfzbox(self, searchindex):
        for index, fzbox in self.fz_data:
            if index == searchindex:
                return fzbox
        else:
            return None

    def match(self, box, partialdatamatch):
        content = box.content
        if not isinstance(content, PartialDataStruct):
            return False

        cankeep = {}
        for index, subbox in content.data:
            selfbox = self.getfzbox(index)
            if selfbox is not None and selfbox.is_constant_equal(subbox):
                cankeep[index] = None
        fullmatch = len(cankeep) == len(self.fz_data)
        try:
            prevkeep = partialdatamatch[box]
        except KeyError:
            partialdatamatch[box] = cankeep
        else:
            if prevkeep is not None:
                d = {}
                for index in prevkeep:
                    if index in cankeep:
                        d[index] = None
                partialdatamatch[box] = d
        return fullmatch


class PartialDataStruct(AbstractContainer):

    def __init__(self):
        self.data = []

    def op_getfield(self, jitstate, fielddesc):
        searchindex = fielddesc.fieldindex
        for index, box in self.data:
            if index == searchindex:
                return box
        else:
            return None

    def remember_field(self, fielddesc, box):
        searchindex = fielddesc.fieldindex
        for i in range(len(self.data)):
            if self.data[i][0] == searchindex:
                self.data[i] = searchindex, box
                return
        else:
            self.data.append((searchindex, box))

    def partialfreeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = FrozenPartialDataStruct()
        for index, box in self.data:
            if box.is_constant():
                frozenbox = box.freeze(memo)
                result.fz_data.append((index, frozenbox))
        if len(result.fz_data) == 0:
            return None
        else:
            return result

    def copy(self, memo):
        result = PartialDataStruct()
        for index, box in self.data:
            result.data.append((index, box.copy(memo)))
        return result

    def replace(self, memo):
        for i in range(len(self.data)):
            index, box = self.data[i]
            box = box.replace(memo)
            self.data[i] = index, box

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for index, box in self.data:
                box.enter_block(incoming, memo)

    def cleanup_partial_data(self, keep):
        if keep is None:
            return None
        j = 0
        data = self.data
        for i in range(len(data)):
            item = data[i]
            if item[0] in keep:
                data[j] = item
                j += 1
        if j == 0:
            return None
        del data[j:]
        return self
