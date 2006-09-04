import operator
from pypy.rpython.lltypesystem import lltype
from pypy.jit.timeshifter import rvalue

class AbstractContainer(object):
    pass

# ____________________________________________________________

class cachedtype(type):
    """Metaclass for classes that should only have one instance per
    tuple of arguments given to the constructor."""

    def __init__(selfcls, name, bases, dict):
        super(cachedtype, selfcls).__init__(name, bases, dict)
        selfcls._instancecache = {}

    def __call__(selfcls, *args):
        d = selfcls._instancecache
        try:
            return d[args]
        except KeyError:
            instance = d[args] = selfcls.__new__(selfcls, *args)
            instance.__init__(*args)
            return instance


class StructTypeDesc(object):
    __metaclass__ = cachedtype
    firstsubstructdesc = None

    def __init__(self, RGenOp, TYPE):
        self.TYPE = TYPE
        self.PTRTYPE = lltype.Ptr(TYPE)
        self.alloctoken = RGenOp.allocToken(self.TYPE)
        self.ptrkind = RGenOp.kindToken(self.PTRTYPE)
        innermostdesc = self

        fielddescs = []
        fielddesc_by_name = {}
        for name in self.TYPE._names:
            FIELDTYPE = getattr(self.TYPE, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                substructdesc = StructTypeDesc(RGenOp, FIELDTYPE)
                assert name == self.TYPE._names[0], (
                    "unsupported: inlined substructures not as first field")
                fielddescs.extend(substructdesc.fielddescs)
                self.firstsubstructdesc = substructdesc
                innermostdesc = substructdesc.innermostdesc
            else:
                index = len(fielddescs)
                desc = StructFieldDesc(RGenOp, self.PTRTYPE, name, index)
                fielddescs.append(desc)
                fielddesc_by_name[name] = desc
        self.fielddescs = fielddescs
        self.fielddesc_by_name = fielddesc_by_name
        self.innermostdesc = innermostdesc

    def getfielddesc(self, name):
        return self.fielddesc_by_name[name]

    def ll_factory(self):
        vstruct = VirtualStruct(self)
        box = rvalue.PtrRedBox(self.innermostdesc.ptrkind)
        box.content = vstruct
        vstruct.ownbox = box
        return box

    def _freeze_(self):
        return True

    def compact_repr(self): # goes in ll helper names
        return "Desc_%s" % (self.TYPE._short_name(),)

# XXX basic field descs for now
class FieldDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, PTRTYPE, RESTYPE):
        self.PTRTYPE = PTRTYPE
        if isinstance(RESTYPE, lltype.ContainerType):
            RESTYPE = lltype.Ptr(RESTYPE)
        self.RESTYPE = RESTYPE
        self.ptrkind = RGenOp.kindToken(PTRTYPE)
        self.kind = RGenOp.kindToken(RESTYPE)
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

class ArrayFieldDesc(FieldDesc):
    def __init__(self, RGenOp, PTRTYPE):
        assert isinstance(PTRTYPE.TO, lltype.Array)
        FieldDesc.__init__(self, RGenOp, PTRTYPE, PTRTYPE.TO.OF)
        self.arraytoken = RGenOp.arrayToken(PTRTYPE.TO)
        self.indexkind = RGenOp.kindToken(lltype.Signed)

# ____________________________________________________________

class FrozenVirtualStruct(AbstractContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.fz_content_boxes initialized later

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
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

        

class VirtualStruct(AbstractContainer):

    def __init__(self, typedesc):
        self.typedesc = typedesc
        self.content_boxes = [desc.redboxcls(desc.kind,
                                             desc.gv_default)
                              for desc in typedesc.fielddescs]
        #self.ownbox = ... set in ll_factory()

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.content_boxes:
                box.enter_block(incoming, memo)

    def force_runtime_container(self, builder):
        typedesc = self.typedesc
        boxes = self.content_boxes
        self.content_boxes = None
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
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = FrozenVirtualStruct(self.typedesc)
            frozens = [box.freeze(memo) for box in self.content_boxes]
            result.fz_content_boxes = frozens
            return result
        
    def copy(self, memo):
        contmemo = memo.containers
        try:
            return contmemo[self]
        except KeyError:
            result = contmemo[self] = VirtualStruct(self.typedesc)
            result.content_boxes = [box.copy(memo)
                                    for box in self.content_boxes]
            result.ownbox = self.ownbox.copy(memo)
            return result

    def replace(self, memo):
        contmemo = memo.containers
        if self not in contmemo:
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
