import operator, weakref
from pypy.rpython.lltypesystem import lltype, lloperation, llmemory
from pypy.rpython import rgenop
from pypy.jit.timeshifter import rvalue

FOLDABLE_OPS = dict.fromkeys(lloperation.enum_foldable_ops())


##def make_types_const(TYPES):
##    n = len(TYPES)
##    l = lltype.malloc(rgenop.VARLIST.TO, n)
##    for i in range(n):
##        l[i] = rgenop.constTYPE(TYPES[i])
##    return l


##class RedBox(object):

##    def same_constant(self, other):
##        return False

##    def getallvariables(self, jitstate, result_gv, memo):
##        pass

##    def copybox(self, newblock, gv_type, memo):
##        try:
##            return memo[self]
##        except KeyError:
##            return self._copybox(newblock, gv_type, memo)

##    def match(self, jitstate, newbox, incoming, memo):
##        if self in memo:
##            return memo[self] is newbox
##        if newbox in memo:
##            return memo[newbox] is self
##        memo[self] = newbox
##        memo[newbox] = self
##        return self._match(jitstate, newbox, incoming, memo)

##    def union_for_new_block(self, jitstate, newbox, newblock,
##                            gv_type, incoming, memo):
##        try:
##            return memo[newbox]
##        except KeyError:
##            return self._union_for_new_block(jitstate, newbox, newblock,
##                                             gv_type, incoming, memo)

##    # generic implementation of some operations
##    def op_getfield(self, jitstate, fielddesc):
##        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
##        op_args[0] = self.getgenvar(jitstate)
##        op_args[1] = fielddesc.gv_fieldname
##        genvar = rgenop.genop(jitstate.curblock, 'getfield', op_args,
##                              fielddesc.gv_resulttype)
##        return VarRedBox(genvar)

##    def op_setfield(self, jitstate, fielddesc, valuebox):
##        op_args = lltype.malloc(rgenop.VARLIST.TO, 3)
##        op_args[0] = self.getgenvar(jitstate)
##        op_args[1] = fielddesc.gv_fieldname
##        op_args[2] = valuebox.getgenvar(jitstate)
##        rgenop.genop(jitstate.curblock, 'setfield', op_args,
##                              rgenop.gv_Void)

##    def op_getsubstruct(self, jitstate, fielddesc):
##        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
##        op_args[0] = self.getgenvar(jitstate)
##        op_args[1] = fielddesc.gv_fieldname
##        genvar = rgenop.genop(jitstate.curblock, 'getsubstruct', op_args,
##                              fielddesc.gv_resulttype)
##        return VarRedBox(genvar)


##class VarRedBox(RedBox):
##    "A red box that contains a run-time variable."

##    def __init__(self, genvar):
##        self.genvar = genvar

##    def getgenvar(self, jitstate):
##        return self.genvar

##    def getallvariables(self, jitstate, result_gv, memo):
##        if self not in memo:
##            result_gv.append(self.genvar)
##            memo[self] = None

##    def _copybox(self, newblock, gv_type, memo):
##        newgenvar = rgenop.geninputarg(newblock, gv_type)
##        memo[self] = newbox = VarRedBox(newgenvar)
##        return newbox

##        incoming.append(newbox.getgenvar(jitstate))
##        return True

##    def _match(self, jitstate, newbox, incoming, memo):
##        incoming.append(newbox.getgenvar(jitstate))
##        return True

##    def _union_for_new_block(self, jitstate, newbox, newblock,
##                             gv_type, incoming, memo):
##        incoming.append(newbox.getgenvar(jitstate))
##        newgenvar = rgenop.geninputarg(newblock, gv_type)
##        memo[newbox] = newnewbox = VarRedBox(newgenvar)
##        return newnewbox


##VCONTAINER = lltype.GcStruct("vcontainer")

##class ContainerRedBox(RedBox):
##    def __init__(self, envelope, content_addr):
##        self.envelope = envelope
##        self.content_addr = content_addr

##    def getgenvar(self, jitstate): # no support at the moment
##        raise RuntimeError("cannot force virtual containers")

##    def ll_make_container_box(envelope, content_addr):
##        return ContainerRedBox(envelope, content_addr)
##    ll_make_container_box = staticmethod(ll_make_container_box)

##    def ll_make_subcontainer_box(box, content_addr):
##        return ContainerRedBox(box.envelope, content_addr)
##    ll_make_subcontainer_box = staticmethod(ll_make_subcontainer_box)


##def ll_getenvelope(box):
##    assert isinstance(box, ContainerRedBox)
##    return box.envelope

##def ll_getcontent(box):
##    assert isinstance(box, ContainerRedBox)
##    return box.content_addr


##class BigRedBox(RedBox):
##    "A (big) red box that contains (small) red boxes inside."

##    #def __init__(self, content_boxes):
##    #    self.content_boxes = content_boxes

##    def op_getfield(self, jitstate, fielddesc):
##        if self.content_boxes is None:
##            return RedBox.op_getfield(self, jitstate, fielddesc)
##        else:
##            return self.content_boxes[fielddesc.fieldindex]

##    def op_setfield(self, jitstate, fielddesc, valuebox):
##        if self.content_boxes is None:
##            RedBox.op_setfield(self, jitstate, fielddesc, valuebox)
##        else:
##            self.content_boxes[fielddesc.fieldindex] = valuebox

##    def op_getsubstruct(self, jitstate, fielddesc):
##        if self.content_boxes is None:
##            return RedBox.op_getsubstruct(self, jitstate, fielddesc)
##        else:
##            return self.content_boxes[fielddesc.fieldindex]


##class VirtualRedBox(BigRedBox):
##    "A red box that contains (for now) a virtual Struct."

##    def __init__(self, typedesc):
##        self.content_boxes = typedesc.build_content_boxes(self)
##        self.typedesc = typedesc
##        self.genvar = rgenop.nullvar

##    def getgenvar(self, jitstate):
##        if not self.genvar:
##            typedesc = self.typedesc
##            boxes = self.content_boxes
##            self.content_boxes = None
##            op_args = lltype.malloc(rgenop.VARLIST.TO, 1)
##            op_args[0] = typedesc.gv_type
##            self.genvar = rgenop.genop(jitstate.curblock, 'malloc', op_args,
##                                       typedesc.gv_ptrtype)
##            typedesc.materialize_content(jitstate, self.genvar, boxes)
##        return self.genvar

##    def is_forced(self):
##        return bool(self.genvar)

##    def getallvariables(self, jitstate, result_gv, memo):
##        if self.genvar:
##            if self not in memo:
##                result_gv.append(self.genvar)
##                memo[self] = None
##        else:
##            for smallbox in self.content_boxes:
##                smallbox.getallvariables(jitstate, result_gv, memo)

##    def _copybox(self, newblock, gv_type, memo):
##        if self.genvar:
##            newgenvar = rgenop.geninputarg(newblock, gv_type)
##            memo[self] = newbox = VarRedBox(newgenvar)
##            return newbox
##        bigbox = VirtualRedBox(self.typedesc)
##        memo[self] = bigbox
##        for i in range(len(bigbox.content_boxes)):
##            gv_fldtype = self.typedesc.fielddescs[i].gv_resulttype
##            bigbox.content_boxes[i] = self.content_boxes[i].copybox(newblock,
##                                                                    gv_fldtype,
##                                                                    memo)
##        return bigbox

##    def _match(self, jitstate, newbox, incoming, memo):
##        if self.genvar:
##            incoming.append(newbox.getgenvar(jitstate))
##            return True
##        if not isinstance(newbox, VirtualRedBox):
##            return False
##        for i in range(len(self.content_boxes)):
##            mysmallbox  = self.content_boxes[i]
##            newsmallbox = newbox.content_boxes[i]
##            if not mysmallbox.match(jitstate, newsmallbox, incoming, memo):
##                return False
##        else:
##            return True

##    def inlined_structs_are_compatible(self, newbox):
##        return (isinstance(newbox, VirtualRedBox) and not newbox.genvar and
##                self.typedesc.compare_content_boxes(self.content_boxes,
##                                                    newbox.content_boxes))

##    def _union_for_new_block(self, jitstate, newbox, newblock,
##                             gv_type, incoming, memo):
##        if self.genvar or not self.inlined_structs_are_compatible(newbox):
##            incoming.append(newbox.getgenvar(jitstate))
##            newgenvar = rgenop.geninputarg(newblock, gv_type)
##            memo[newbox] = newnewbox = VarRedBox(newgenvar)
##            return newnewbox
##        bigbox = VirtualRedBox(self.typedesc)
##        memo[newbox] = bigbox
##        for i in range(len(bigbox.content_boxes)):
##            gv_fldtype = self.typedesc.fielddescs[i].gv_resulttype
##            box = self.content_boxes[i]
##            bigbox.content_boxes[i] = box.union_for_new_block(
##                jitstate,
##                newbox.content_boxes[i],
##                newblock,
##                gv_fldtype,
##                incoming,
##                memo)
##        return bigbox


##class SubVirtualRedBox(BigRedBox):

##    def __init__(self, parentbox, fielddesc):
##        self.parentbox = parentbox
##        self.fielddesc = fielddesc
##        typedesc = fielddesc.inlined_typedesc
##        self.content_boxes = typedesc.build_content_boxes(self)

##    def getgenvar(self, jitstate):
##        gv = self.parentbox.getgenvar(jitstate)
##        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
##        op_args[0] = gv
##        op_args[1] = self.fielddesc.gv_fieldname
##        genvar = rgenop.genop(jitstate.curblock, 'getsubstruct', op_args,
##                              self.fielddesc.gv_resulttype)
##        return genvar

##    def is_forced(self):
##        return self.parentbox.is_forced()

##    def getallvariables(self, jitstate, result_gv, memo):
##        if self.is_forced():
##            if self not in memo:
##                result_gv.append(self.getgenvar(jitstate))
##                memo[self] = None
##        else:
##            for smallbox in self.content_boxes:
##                smallbox.getallvariables(jitstate, result_gv, memo)

##    def _copybox(self, newblock, gv_type, memo):
##        if self.is_forced():
##            newgenvar = rgenop.geninputarg(newblock, gv_type)
##            memo[self] = newbox = VarRedBox(newgenvar)
##            return newbox
##        bigbox = SubVirtualRedBox(None, self.fielddesc)
##        memo[self] = bigbox
##        gv_parenttype = self.fielddesc.parenttypedesc.gv_ptrtype
##        parentcopybox = self.parentbox.copybox(newblock, gv_parenttype, memo)
##        bigbox.parentbox = parentcopybox
##        typedesc = self.fielddesc.inlined_typedesc
##        for i in range(len(bigbox.content_boxes)):
##            gv_fldtype = typedesc.fielddescs[i].gv_resulttype
##            bigbox.content_boxes[i] = self.content_boxes[i].copybox(newblock,
##                                                                    gv_fldtype,
##                                                                    memo)
##        return bigbox

##    def _match(self, jitstate, newbox, incoming, memo):
##        if self.is_forced():
##            incoming.append(newbox.getgenvar(jitstate))
##            return True
##        if not (isinstance(newbox, SubVirtualRedBox) and
##                self.fielddesc is newbox.fielddesc and
##                self.parentbox.match(jitstate, newbox.parentbox,
##                                     incoming, memo)):
##            return False
##        for i in range(len(self.content_boxes)):
##            mysmallbox  = self.content_boxes[i]
##            newsmallbox = newbox.content_boxes[i]
##            if not mysmallbox.match(jitstate, newsmallbox, incoming, memo):
##                return False
##        else:
##            return True

##    def inlined_structs_are_compatible(self, newbox):
##        if (isinstance(newbox, SubVirtualRedBox) and not newbox.is_forced() and
##            self.fielddesc is newbox.fielddesc):
##            return self.parentbox.inlined_structs_are_compatible(
##                newbox.parentbox)
##        else:
##            return False

##    def _union_for_new_block(self, jitstate, newbox, newblock,
##                             gv_type, incoming, memo):
##        if self.is_forced() or not self.inlined_structs_are_compatible(newbox):
##            incoming.append(newbox.getgenvar(jitstate))
##            newgenvar = rgenop.geninputarg(newblock, gv_type)
##            memo[newbox] = newnewbox = VarRedBox(newgenvar)
##            return newnewbox
##        assert isinstance(newbox, SubVirtualRedBox)
##        bigbox = SubVirtualRedBox(None, self.fielddesc)
##        memo[newbox] = bigbox
##        gv_parenttype = self.fielddesc.parenttypedesc.gv_ptrtype
##        parentcopybox = self.parentbox.union_for_new_block(jitstate,
##                                                           newbox.parentbox,
##                                                           newblock,
##                                                           gv_parenttype,
##                                                           incoming,
##                                                           memo)
##        bigbox.parentbox = parentcopybox
##        typedesc = self.fielddesc.inlined_typedesc
##        for i in range(len(bigbox.content_boxes)):
##            gv_fldtype = typedesc.fielddescs[i].gv_resulttype
##            box = self.content_boxes[i]
##            bigbox.content_boxes[i] = box.union_for_new_block(
##                jitstate,
##                newbox.content_boxes[i],
##                newblock,
##                gv_fldtype,
##                incoming,
##                memo)
##        return bigbox


##class ConstRedBox(RedBox):
##    "A red box that contains a run-time constant."

##    def __init__(self, genvar):
##        self.genvar = genvar

##    def getgenvar(self, jitstate):
##        return self.genvar

##    def copybox(self, newblock, gv_type, memo):
##        return self

##    def match(self, jitstate, newbox, incoming, memo):
##        return self.same_constant(newbox)

##    def _union_for_new_block(self, jitstate, newbox, newblock,
##                             gv_type, incoming, memo):
##        if self.same_constant(newbox):
##            newnewbox = newbox
##        else:
##            incoming.append(newbox.getgenvar(jitstate))
##            newgenvar = rgenop.geninputarg(newblock, gv_type)
##            newnewbox = VarRedBox(newgenvar)
##        memo[newbox] = newnewbox
##        return newnewbox

##    def ll_fromvalue(value):
##        T = lltype.typeOf(value)
##        gv = rgenop.genconst(value)
##        if isinstance(T, lltype.Ptr):
##            return AddrRedBox(gv)
##        elif T is lltype.Float:
##            return DoubleRedBox(gv)
##        else:
##            assert isinstance(T, lltype.Primitive)
##            assert T is not lltype.Void, "cannot make red boxes of voids"
##            # XXX what about long longs?
##            return IntRedBox(gv)
##    ll_fromvalue = staticmethod(ll_fromvalue)

##    def ll_getvalue(self, T):
##        # note: this is specialized by low-level type T, as a low-level helper
##        return rgenop.revealconst(T, self.genvar)

##def ll_getvalue(box, T):
##    return box.ll_getvalue(T)
        

##class IntRedBox(ConstRedBox):
##    "A red box that contains a constant integer-like value."

##    def same_constant(self, other):
##        return (isinstance(other, IntRedBox) and
##                self.ll_getvalue(lltype.Signed) == other.ll_getvalue(lltype.Signed))


##class DoubleRedBox(ConstRedBox):
##    "A red box that contains a constant double-precision floating point value."

##    def same_constant(self, other):
##        return (isinstance(other, DoubleRedBox) and
##                self.ll_getvalue(lltype.Float) == other.ll_getvalue(lltype.Float))


##class AddrRedBox(ConstRedBox):
##    "A red box that contains a constant address."

##    def same_constant(self, other):
##        return (isinstance(other, AddrRedBox) and
##                self.ll_getvalue(llmemory.Address) == other.ll_getvalue(llmemory.Address))


# ____________________________________________________________
# emit ops


class OpDesc(object):
    """
    Description of a low-level operation
    that can be passed around to low level helpers
    to inform op generation
    """
    
    def _freeze_(self):
        return True

    def __init__(self, opname, ARGS, RESULT):
        self.opname = opname
        self.llop = lloperation.LL_OPERATIONS[opname]
        self.nb_args = len(ARGS)
        self.ARGS = ARGS
        self.RESULT = RESULT
        self.gv_RESULT = rgenop.constTYPE(RESULT)
        self.redboxcls = rvalue.ll_redboxcls(RESULT)
        self.canfold = opname in FOLDABLE_OPS

    def __getattr__(self, name): # .ARGx -> .ARGS[x]
        if name.startswith('ARG'):
            index = int(name[3:])
            return self.ARGS[index]
        else:
            raise AttributeError("don't know about %r in OpDesc" % name)

    def compact_repr(self): # goes in ll helper names
        return self.opname.upper()

_opdesc_cache = {}

def make_opdesc(hop):
    hrtyper = hop.rtyper
    op_key = (hop.spaceop.opname,
              tuple([hrtyper.originalconcretetype(s_arg) for s_arg in hop.args_s]),
              hrtyper.originalconcretetype(hop.s_result))
    try:
        return _opdesc_cache[op_key]
    except KeyError:
        opdesc = OpDesc(*op_key)
        _opdesc_cache[op_key] = opdesc
        return opdesc

def ll_generate_operation1(opdesc, jitstate, argbox):
    ARG0 = opdesc.ARG0
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if opdesc.canfold and argbox.is_constant():
        arg = rvalue.ll_getvalue(argbox, ARG0)
        res = opdesc.llop(RESULT, arg)
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 1)
    op_args[0] = argbox.getgenvar(jitstate)
    genvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                          opdesc.gv_RESULT)
    return opdesc.redboxcls(opdesc.gv_RESULT, genvar)

def ll_generate_operation2(opdesc, jitstate, argbox0, argbox1):
    ARG0 = opdesc.ARG0
    ARG1 = opdesc.ARG1
    RESULT = opdesc.RESULT
    opname = opdesc.name
    if opdesc.canfold and argbox0.is_constant() and argbox1.is_constant():
        # const propagate
        arg0 = rvalue.ll_getvalue(argbox0, ARG0)
        arg1 = rvalue.ll_getvalue(argbox1, ARG1)
        res = opdesc.llop(RESULT, arg0, arg1)
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
    op_args[0] = argbox0.getgenvar(jitstate)
    op_args[1] = argbox1.getgenvar(jitstate)
    genvar = rgenop.genop(jitstate.curblock, opdesc.opname, op_args,
                          opdesc.gv_RESULT)
    return opdesc.redboxcls(opdesc.gv_RESULT, genvar)

## class StructTypeDesc(object):
##     _type_cache = weakref.WeakKeyDictionary()

##     def __init__(self, TYPE):
##         self.TYPE = TYPE
##         self.PTRTYPE = lltype.Ptr(TYPE)
##         self.gv_type = rgenop.constTYPE(self.TYPE)
##         self.gv_ptrtype = rgenop.constTYPE(self.PTRTYPE)

##     def setup(self):
##         self.fielddescs = [StructFieldDesc.make(self.PTRTYPE, name)
##                            for name in self.TYPE._names]
##         defls = []
##         for desc in self.fielddescs:
##             if desc.inlined_typedesc is not None:
##                 defaultbox = None
##             else:
##                 defaultvalue = desc.RESTYPE._defl()
##                 defaultbox = rvalue.ll_fromvalue(defaultvalue)
##             defls.append(defaultbox)
##         self.default_boxes = defls

##     def build_content_boxes(self, parentbox):
##         # make a'content_boxes' list based on the typedesc's default_boxes,
##         # building nested SubVirtualRedBoxes for inlined substructs
##         clist = []
##         for i in range(len(self.fielddescs)):
##             fielddesc = self.fielddescs[i]
##             if fielddesc.inlined_typedesc:
##                 box = SubVirtualRedBox(parentbox, fielddesc)
##             else:
##                 box = self.default_boxes[i]
##             clist.append(box)
##         return clist

##     def compare_content_boxes(self, content_boxes_1, content_boxes_2):
##         for i in range(len(self.fielddescs)):
##             fielddesc = self.fielddescs[i]
##             if fielddesc.inlined_typedesc:
##                 box1 = content_boxes_1[i]
##                 box2 = content_boxes_2[i]
##                 assert isinstance(box1, BigRedBox)
##                 assert isinstance(box2, BigRedBox)
##                 if not fielddesc.inlined_typedesc.compare_content_boxes(
##                     box1.content_boxes, box2.content_boxes):
##                     return False
##         else:
##             return True

##     def materialize_content(self, jitstate, gv, boxes):
##         for i in range(len(boxes)):
##             smallbox = boxes[i]
##             fielddesc = self.fielddescs[i]
##             if fielddesc.inlined_typedesc:
##                 op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
##                 op_args[0] = gv
##                 op_args[1] = fielddesc.gv_fieldname
##                 gv_sub = rgenop.genop(jitstate.curblock, 'getsubstruct',
##                                       op_args, fielddesc.gv_resulttype)
##                 assert isinstance(smallbox, SubVirtualRedBox)
##                 subboxes = smallbox.content_boxes
##                 smallbox.content_boxes = None
##                 fielddesc.inlined_typedesc.materialize_content(jitstate,
##                                                                gv_sub,
##                                                                subboxes)
##             else:
##                 op_args = lltype.malloc(rgenop.VARLIST.TO, 3)
##                 op_args[0] = gv
##                 op_args[1] = fielddesc.gv_fieldname
##                 op_args[2] = smallbox.getgenvar(jitstate)
##                 rgenop.genop(jitstate.curblock, 'setfield', op_args,
##                              rgenop.gv_Void)

##     def make(T):
##         try:
##             return StructTypeDesc._type_cache[T]
##         except KeyError:
##             desc = StructTypeDesc._type_cache[T] = StructTypeDesc(T)
##             desc.setup()
##             return desc
##     make = staticmethod(make)

##     def ll_factory(self):
##         return VirtualRedBox(self)

##     def _freeze_(self):
##         return True

##     def compact_repr(self): # goes in ll helper names
##         return "Desc_%s" % (self.TYPE._short_name(),)

## class FieldDesc(object):
##     _fielddesc_cache = weakref.WeakKeyDictionary()

##     def __init__(self, PTRTYPE, RESTYPE):
##         self.PTRTYPE = PTRTYPE
##         if isinstance(RESTYPE, lltype.ContainerType):
##             RESTYPE = lltype.Ptr(RESTYPE)
##         self.RESTYPE = RESTYPE
##         self.gv_resulttype = rgenop.constTYPE(RESTYPE)
##         self.redboxcls = rvalue.ll_redboxcls(RESTYPE)
##         self.immutable = PTRTYPE.TO._hints.get('immutable', False)

##     def _freeze_(self):
##         return True

##     def make(cls, PTRTYPE, *args):
##         T = PTRTYPE.TO
##         cache = FieldDesc._fielddesc_cache.setdefault(T, {})
##         try:
##             return cache[args]
##         except KeyError:
##             fdesc = cache[args] = cls(PTRTYPE, *args)
##             fdesc.setup()
##             return fdesc
##     make = classmethod(make)

## class StructFieldDesc(FieldDesc):
##     def __init__(self, PTRTYPE, fieldname):
##         assert isinstance(PTRTYPE.TO, lltype.Struct)
##         RES1 = getattr(PTRTYPE.TO, fieldname)
##         FieldDesc.__init__(self, PTRTYPE, RES1)
##         self.fieldname = fieldname
##         self.gv_fieldname = rgenop.constFieldName(fieldname)
##         self.fieldindex = operator.indexOf(PTRTYPE.TO._names, fieldname)
##         if isinstance(RES1, lltype.Struct):
##             # inlined substructure
##             self.inlined_typedesc = StructTypeDesc.make(RES1)
## ##        elif isinstance(RES1, lltype.Array):
## ##            # inlined array XXX in-progress
## ##            self.inlined_typedesc = ArrayTypeDesc.make(RES1)
##         else:
##             self.inlined_typedesc = None

##     def setup(self):
##         self.parenttypedesc = StructTypeDesc.make(self.PTRTYPE.TO)

##     def compact_repr(self): # goes in ll helper names
##         return "Fld_%s_in_%s" % (self.fieldname, self.PTRTYPE._short_name())

## class ArrayFieldDesc(FieldDesc):
##     def __init__(self, PTRTYPE):
##         assert isinstance(PTRTYPE.TO, lltype.Array)
##         FieldDesc.__init__(self, PTRTYPE, PTRTYPE.TO.OF)
##     def setup(self):
##         pass

def ll_generate_getfield(jitstate, fielddesc, argbox):
    if fielddesc.immutable and argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
        op_args[0] = argbox.getgenvar(jitstate)
        op_args[1] = fielddesc.fieldname_gv[-1]
        genvar = rgenop.genop(jitstate.curblock, 'getfield', op_args,
                              fielddesc.gv_resulttype)
        return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)        
    else:
        return argbox.content.op_getfield(jitstate, fielddesc)

def ll_generate_setfield(jitstate, fielddesc, destbox, valuebox):
    assert isinstance(destbox, rvalue.PtrRedBox)
    if destbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 3)
        op_args[0] = destbox.getgenvar(jitstate)
        op_args[1] = fielddesc.fieldname_gv[-1]
        op_args[2] = valuebox.getgenvar(jitstate)
        rgenop.genop(jitstate.curblock, 'setfield', op_args,
                     rgenop.gv_Void)       
    else:
        destbox.content.op_setfield(jitstate, fielddesc, valuebox)

def ll_generate_getsubstruct(jitstate, fielddesc, argbox):
    if argbox.is_constant():
        res = getattr(rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE),
                      fielddesc.fieldname)
        return rvalue.ll_fromvalue(res)
    assert isinstance(argbox, rvalue.PtrRedBox)
    if argbox.content is None:
        op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
        op_args[0] = argbox.getgenvar(jitstate)
        op_args[1] = fielddesc.gv_fieldname
        genvar = rgenop.genop(jitstate.curblock, 'getsubstruct', op_args,
                              fielddesc.gv_resulttype)
        return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)        
    else:
        return argbox.content.op_getsubstruct(jitstate, fielddesc)


def ll_generate_getarrayitem(jitstate, fielddesc, argbox, indexbox):
    if fielddesc.immutable and argbox.is_constant() and indexbox.is_constant():
        array = rvalue.ll_getvalue(argbox, fielddesc.PTRTYPE)
        res = array[rvalue.ll_getvalue(indexbox, lltype.Signed)]
        return rvalue.ll_fromvalue(res)
    op_args = lltype.malloc(rgenop.VARLIST.TO, 2)
    op_args[0] = argbox.getgenvar(jitstate)
    op_args[1] = indexbox.getgenvar(jitstate)
    genvar = rgenop.genop(jitstate.curblock, 'getarrayitem', op_args,
                          fielddesc.gv_resulttype)
    return fielddesc.redboxcls(fielddesc.gv_resulttype, genvar)

##def ll_generate_malloc(jitstate, gv_type, gv_resulttype):
##    op_args = lltype.malloc(rgenop.VARLIST.TO, 1)
##    op_args[0] = gv_type
##    genvar = rgenop.genop(jitstate.curblock, 'malloc', op_args,
##                          gv_resulttype)    
##    return VarRedBox(genvar)

# ____________________________________________________________
# other jitstate/graph level operations


def retrieve_jitstate_for_merge(states_dic, jitstate, key, redboxes):
    if key not in states_dic:
        memo = rvalue.freeze_memo()
        frozens = [redbox.freeze(memo) for redbox in redboxes]
        memo = rvalue.exactmatch_memo()
        outgoingvarboxes = []
        for i in range(len(redboxes)):
            res = frozens[i].exactmatch(redboxes[i], outgoingvarboxes, memo)
            assert res, "exactmatch() failed"
        newblock = rgenop.newblock()
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(None))
            box.genvar = rgenop.geninputarg(newblock, box.gv_type)
        rgenop.closelink(jitstate.curoutgoinglink, linkargs, newblock)
        jitstate.curblock = newblock
        jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
        states_dic[key] = frozens, newblock
        return jitstate

    frozens, oldblock = states_dic[key]
    memo = rvalue.exactmatch_memo()
    outgoingvarboxes = []
    exactmatch = True
    for i in range(len(redboxes)):
        frozen = frozens[i]
        if not frozen.exactmatch(redboxes[i], outgoingvarboxes, memo):
            exactmatch = False

    if exactmatch:
        jitstate = dyn_enter_block(jitstate, outgoingvarboxes)
        linkargs = []
        for box in outgoingvarboxes:
            linkargs.append(box.getgenvar(jitstate))
        link = rgenop.closeblock1(jitstate.curblock)
        rgenop.closelink(link, linkargs, oldblock)
        return None
    
    # Make a more general block
    jitstate = dyn_enter_block(jitstate, outgoingvarboxes)
    newblock = rgenop.newblock()
    linkargs = []
    for box in outgoingvarboxes:
        linkargs.append(box.getgenvar(jitstate))
        box.genvar = rgenop.geninputarg(newblock, box.gv_type)
    link = rgenop.closeblock1(jitstate.curblock)
    rgenop.closelink(link, linkargs, newblock)
    jitstate.curblock = newblock
    #jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    memo = rvalue.freeze_memo()
    frozens = [redbox.freeze(memo) for redbox in redboxes]
    states_dic[key] = frozens, newblock
    return jitstate
    
##     newblock = rgenop.newblock()
##     incoming = []
##     memo = {}
##     for i in range(len(redboxes)):
##         oldbox = oldboxes[i]
##         newbox = redboxes[i]
##         redboxes[i] = oldbox.union_for_new_block(jitstate, newbox, newblock,
##                                                  types_gv[i], incoming, memo)
## ##        if not oldbox.same_constant(newbox):
## ##            incoming.append(newbox.getgenvar(jitstate))
## ##            newgenvar = rgenop.geninputarg(newblock, TYPES[i])
## ##            redboxes[i] = VarRedBox(newgenvar)
##     link = rgenop.closeblock1(jitstate.curblock)
##     rgenop.closelink(link, incoming, newblock)
##     jitstate.curblock = newblock
##     #jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
##     states_dic[key] = redboxes, newblock
##     return jitstate
retrieve_jitstate_for_merge._annspecialcase_ = "specialize:arglltype(2)"
    
def enter_block(jitstate, redboxes):
    newblock = rgenop.newblock()
    incoming = []
    memo = rvalue.enter_block_memo()
    for i in range(len(redboxes)):
        redboxes[i].enter_block(newblock, incoming, memo)
    rgenop.closelink(jitstate.curoutgoinglink, incoming, newblock)
    jitstate.curblock = newblock
    jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    return jitstate

def dyn_enter_block(jitstate, redboxes):
    newblock = rgenop.newblock()
    incoming = []
    memo = rvalue.enter_block_memo()
    for i in range(len(redboxes)):
        redboxes[i].enter_block(newblock, incoming, memo)
    rgenop.closelink(jitstate.curoutgoinglink, incoming, newblock)
    jitstate.curblock = newblock
    jitstate.curoutgoinglink = lltype.nullptr(rgenop.LINK.TO)
    return jitstate

def leave_block(jitstate):
    jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)
    return jitstate

def leave_block_split(jitstate, switchredbox, exitindex, redboxes):
    if switchredbox.is_constant():
        jitstate.curoutgoinglink = rgenop.closeblock1(jitstate.curblock)        
        return rvalue.ll_getvalue(switchredbox, lltype.Bool)
    else:
        exitgvar = switchredbox.getgenvar(jitstate)
        linkpair = rgenop.closeblock2(jitstate.curblock, exitgvar)    
        false_link, true_link = linkpair.item0, linkpair.item1
        later_jitstate = jitstate.copystate()
        jitstate.curoutgoinglink = true_link
        later_jitstate.curoutgoinglink = false_link
        memo = rvalue.Memo()
        redboxcopies = [redbox.copy(memo) for redbox in redboxes]        
        jitstate.split_queue.append((exitindex, later_jitstate, redboxcopies))
        return True

def schedule_return(jitstate, redbox):
    jitstate.return_queue.append((jitstate.curoutgoinglink, redbox))

novars = lltype.malloc(rgenop.VARLIST.TO, 0)

def dispatch_next(jitstate, outredboxes, gv_return_type):
    split_queue = jitstate.split_queue
    if split_queue:
        exitindex, later_jitstate, redboxes = split_queue.pop()
        jitstate.curblock = later_jitstate.curblock
        jitstate.curoutgoinglink = later_jitstate.curoutgoinglink
        jitstate.curvalue = later_jitstate.curvalue
        for box in redboxes:
            outredboxes.append(box)
        return exitindex
    return_queue = jitstate.return_queue
    first_redbox = return_queue[0][1]
    finalblock = rgenop.newblock()
##    jitstate.curblock = finalblock
##    if isinstance(first_redbox, ConstRedBox):
##        for link, redbox in return_queue:
##            if not redbox.match(first_redbox):
##                break
##        else:
##            for link, _ in return_queue:
##                rgenop.closelink(link, novars, finalblock)
##            finallink = rgenop.closeblock1(finalblock)
##            jitstate.curoutgoinglink = finallink
##            jitstate.curvalue = first_redbox
##            return -1

    finalvar = rgenop.geninputarg(finalblock, gv_return_type)
    for link, redbox in return_queue:
        newblock = rgenop.newblock()
        incoming = []
        memo = rvalue.enter_block_memo()
        redbox.enter_block(newblock, incoming, memo)
        jitstate.curblock = newblock
        gv_retval = redbox.getgenvar(jitstate)
        rgenop.closelink(link, incoming, newblock)
        newlink = rgenop.closeblock1(newblock)
        rgenop.closelink(newlink, [gv_retval], finalblock)
    finallink = rgenop.closeblock1(finalblock)
    jitstate.curoutgoinglink = finallink
    jitstate.curvalue = finalvar
    return -1

def ll_gvar_from_redbox(jitstate, redbox):
    return redbox.getgenvar(jitstate)

def ll_gvar_from_constant(ll_value):
    return rgenop.genconst(ll_value)

# ____________________________________________________________

class JITState(object):
    # XXX obscure interface

    def setup(self):
        self.return_queue = []
        self.split_queue = []
        self.curblock = rgenop.newblock()
        self.curvalue = rgenop.nullvar

    def end_setup(self):
        self.curoutgoinglink = rgenop.closeblock1(self.curblock)

    def close(self, return_gvar):
        rgenop.closereturnlink(self.curoutgoinglink, return_gvar)

    def copystate(self):
        other = JITState()
        other.return_queue = self.return_queue
        other.split_queue = self.split_queue
        other.curblock = self.curblock
        other.curoutgoinglink = self.curoutgoinglink
        other.curvalue = self.curvalue
        return other

def ll_build_jitstate():
    jitstate = JITState()
    jitstate.setup()
    return jitstate

def ll_int_box(gv_type, gv):
    return rvalue.IntRedBox(gv_type, gv)

def ll_double_box(gv_type, gv):
    return rvalue.DoubleRedBox(gv_type, gv)

def ll_addr_box(gv_type, gv):
    return rvalue.PtrRedBox(gv_type, gv)

def ll_geninputarg(jitstate, gv_TYPE):
    return rgenop.geninputarg(jitstate.curblock, gv_TYPE)

def ll_end_setup_jitstate(jitstate):
    jitstate.end_setup()
    return jitstate.curblock

def ll_close_jitstate(jitstate):
    result_genvar = jitstate.curvalue
    jitstate.close(result_genvar)
