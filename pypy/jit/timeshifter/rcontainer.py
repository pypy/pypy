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

        fielddescs = []
        for name in self.TYPE._names:
            FIELDTYPE = getattr(self.TYPE, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                substructdesc = StructTypeDesc(RGenOp, FIELDTYPE)
                assert name == self.TYPE._names[0], (
                    "unsupported: inlined substructures not as first field")
                self.firstsubstructdesc = substructdesc
                for subfielddesc in substructdesc.fielddescs:
                    dottedname = '%s.%s' % (name, subfielddesc.fieldname)
                    index = len(fielddescs)
                    fielddescs.append(StructFieldDesc(RGenOp, self.PTRTYPE,
                                                      dottedname, index))
            else:
                index = len(fielddescs)
                fielddescs.append(StructFieldDesc(RGenOp, self.PTRTYPE,
                                                  name, index))
        self.fielddescs = fielddescs

    def getfielddesc(self, name):
        index = operator.indexOf(self.TYPE._names, name)
        return self.fielddescs[index]

    def ll_factory(self):
        vstruct = VirtualStruct(self)
        vstruct.substruct_boxes = []
        typedesc = self
        while typedesc is not None:
            box = rvalue.PtrRedBox(typedesc.ptrkind)
            box.content = vstruct
            vstruct.substruct_boxes.append(box)
            typedesc = typedesc.firstsubstructdesc
        return vstruct.substruct_boxes[0]

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
        self.kind = RGenOp.kindToken(RESTYPE)
        self.redboxcls = rvalue.ll_redboxcls(RESTYPE)
        self.immutable = PTRTYPE.TO._hints.get('immutable', False)

    def _freeze_(self):
        return True

class NamedFieldDesc(FieldDesc):

    def __init__(self, RGenOp, PTRTYPE, name):
        FieldDesc.__init__(self, RGenOp, PTRTYPE, getattr(PTRTYPE.TO, name))
        self.structdepth = 0
        T = self.PTRTYPE.TO
        self.fieldname = name
        self.fieldtoken = RGenOp.fieldToken(T, name)
        while (T._names and
               isinstance(getattr(T, T._names[0]), lltype.ContainerType)):
            self.structdepth += 1
            T = getattr(T, T._names[0])

class ArrayFieldDesc(FieldDesc):
    def __init__(self, RGenOp, PTRTYPE):
        assert isinstance(PTRTYPE.TO, lltype.Array)
        FieldDesc.__init__(self, RGenOp, PTRTYPE, PTRTYPE.TO.OF)
        self.arraytoken = RGenOp.arrayToken(PTRTYPE.TO)

class StructFieldDesc(object):
    __metaclass__ = cachedtype

    def __init__(self, RGenOp, PTRTYPE, fieldname, index):
        assert isinstance(PTRTYPE.TO, lltype.Struct)
        RES1 = PTRTYPE.TO
        accessors = []
        for component in fieldname.split('.'):
            LASTSTRUCT = RES1
            accessors.append((RES1, component))
            RES1 = getattr(RES1, component)
        assert not isinstance(RES1, lltype.ContainerType)
        self.PTRTYPE = PTRTYPE
        self.RESTYPE = RES1
        self.kind = RGenOp.kindToken(RES1)
        self.fieldname = fieldname
        self.fieldtokens = [RGenOp.fieldToken(T, component)
                             for T, component in accessors]
        self.fieldindex = index
        self.gv_default = RGenOp.constPrebuiltGlobal(RES1._defl())
        self.redboxcls = rvalue.ll_redboxcls(RES1)
        self.immutable = LASTSTRUCT._hints.get('immutable', False)

    def _freeze_(self):
        return True

    def compact_repr(self): # goes in ll helper names
        return "Fld_%s_in_%s" % (self.fieldname.replace('.','_'),
                                 self.PTRTYPE._short_name())

    def generate_set(self, builder, genvar, box):
        gv_sub = genvar
        for i in range(len(self.fieldtokens)-1):
            gv_sub = builder.genop_getsubstruct(self.fieldtokens[i], gv_sub)
        builder.genop_setfield(self.fieldtokens[-1], gv_sub, box.getgenvar(builder))        

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
                outgoingvarboxes.extend(vstruct.substruct_boxes)
            return ok
        if vstruct in contmemo:
            assert contmemo[vstruct] is not self
            outgoingvarboxes.extend(vstruct.substruct_boxes)
            return False
        if self.typedesc is not vstruct.typedesc:
            outgoingvarboxes.extend(vstruct.substruct_boxes)
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
        #self.substruct_boxes = ...

    def enter_block(self, newblock, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.content_boxes:
                box.enter_block(newblock, incoming, memo)

    def force_runtime_container(self, builder):
        typedesc = self.typedesc
        boxes = self.content_boxes
        self.content_boxes = None
        genvar = builder.genop_malloc_fixedsize(typedesc.alloctoken)
        # force all the boxes pointing to this VirtualStruct
        for box in self.substruct_boxes:
            # XXX using getsubstruct would be nicer
            op_args = [genvar]
            box.genvar = builder.genop('cast_pointer', op_args, box.kind)
            box.content = None
        self.substruct_boxes = None
        fielddescs = typedesc.fielddescs
        for i in range(len(fielddescs)):
            fielddesc = fielddescs[i]
            box = boxes[i]
            # xxx a bit inefficient
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
            result.substruct_boxes = [box.copy(memo)
                                      for box in self.substruct_boxes]
            return result

    def replace(self, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for i in range(len(self.content_boxes)):
                self.content_boxes[i] = self.content_boxes[i].replace(memo)
            for i in range(len(self.substruct_boxes)):
                self.substruct_boxes[i] = self.substruct_boxes[i].replace(memo)

    def op_getfield(self, jitstate, fielddesc):
        return self.content_boxes[fielddesc.fieldindex]

    def op_setfield(self, jitstate, fielddesc, valuebox):
        self.content_boxes[fielddesc.fieldindex] = valuebox

    def op_getsubstruct(self, jitstate, fielddesc):
        #assert fielddesc.fieldindex == 0
        return self.substruct_boxes[-fielddesc.structdepth]
