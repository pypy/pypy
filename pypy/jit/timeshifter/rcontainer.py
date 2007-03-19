import operator
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import cachedtype, cast_base_ptr_to_instance
from pypy.rpython.annlowlevel import base_ptr_lltype, cast_instance_to_base_ptr
from pypy.jit.timeshifter import rvalue
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.timeshifter import rvirtualizable

from pypy.annotation import model as annmodel

from pypy.rpython.lltypesystem import lloperation
debug_print = lloperation.llop.debug_print
debug_pdb = lloperation.llop.debug_pdb

class AbstractContainer(object):
    _attrs_ = []

    def op_getfield(self, jitstate, fielddesc):
        raise NotImplementedError

    def op_setfield(self, jitstate, fielddesc, valuebox):
        raise NotImplementedError

    def op_getsubstruct(self, jitstate, fielddesc):
        raise NotImplementedError


class VirtualContainer(AbstractContainer):
    _attrs_ = []

    allowed_in_virtualizable = False

    def setforced(self, _):
        raise NotImplementedError


class FrozenContainer(AbstractContainer):
    _attrs_ = []

    def exactmatch(self, vstruct, outgoingvarboxes, memo):
        raise NotImplementedError
    
    def unfreeze(self, incomingvarboxes, memo):
        raise NotImplementedError

# ____________________________________________________________

class StructTypeDesc(object):
    __metaclass__ = cachedtype

    VirtualStructCls = None # patched later with VirtualStruct

    _attrs_ =  """TYPE PTRTYPE
                    firstsubstructdesc arrayfielddesc
                    innermostdesc
                    ptrkind
                    alloctoken varsizealloctoken
                    null gv_null
                    fielddescs fielddesc_by_name
                    immutable noidentity
                    materialize
                    devirtualize
                 """.split()
                            

    firstsubstructdesc = None
    materialize = None

    def __new__(cls, hrtyper, TYPE):
        if TYPE._hints.get('virtualizable', False):
            return object.__new__(VirtualizableStructTypeDesc)
        else:
            return object.__new__(StructTypeDesc)
            
    def __init__(self, hrtyper, TYPE):
        RGenOp = hrtyper.RGenOp
        self.TYPE = TYPE
        self.PTRTYPE = lltype.Ptr(TYPE)
        self.ptrkind = RGenOp.kindToken(self.PTRTYPE)

        self.immutable = TYPE._hints.get('immutable', False)
        self.noidentity = TYPE._hints.get('noidentity', False)

        fixsize = not TYPE._is_varsize()

        if fixsize:
            self.alloctoken = RGenOp.allocToken(TYPE)
            
        self.null = self.PTRTYPE._defl()
        self.gv_null = RGenOp.constPrebuiltGlobal(self.null)

        self._compute_fielddescs(hrtyper)

        if self.immutable and self.noidentity:
            self._define_materialize()

        if fixsize:
            self._define_devirtualize()

        
    def _compute_fielddescs(self, hrtyper):
        RGenOp = hrtyper.RGenOp
        TYPE = self.TYPE
        innermostdesc = self
        fielddescs = []
        fielddesc_by_name = {}
        for name in TYPE._names:
            FIELDTYPE = getattr(TYPE, name)
            if isinstance(FIELDTYPE, lltype.ContainerType):
                if isinstance(FIELDTYPE, lltype.Array):
                    self.arrayfielddesc = ArrayFieldDesc(hrtyper, FIELDTYPE)
                    self.varsizealloctoken = RGenOp.varsizeAllocToken(TYPE)
                    continue
                substructdesc = StructTypeDesc(hrtyper, FIELDTYPE)
                assert name == TYPE._names[0], (
                    "unsupported: inlined substructures not as first field")
                fielddescs.extend(substructdesc.fielddescs)
                self.firstsubstructdesc = substructdesc
                innermostdesc = substructdesc.innermostdesc
            else:
                index = len(fielddescs)
                if FIELDTYPE is lltype.Void:
                    desc = None
                else:
                    desc = StructFieldDesc(hrtyper, self.PTRTYPE, name, index)
                    fielddescs.append(desc)
                fielddesc_by_name[name] = desc

        self.fielddescs = fielddescs
        self.fielddesc_by_name = fielddesc_by_name
        self.innermostdesc = innermostdesc        

    def _define_devirtualize(self):
        TYPE = self.TYPE
        PTRTYPE = self.PTRTYPE
        descs = unrolling_iterable(self.fielddescs)

        def make(vrti):
            s = lltype.malloc(TYPE)
            s = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            return s
        
        def fill_into(vablerti, s, base, vrti):
            s = lltype.cast_opaque_ptr(PTRTYPE, s)
            i = 0
            for desc in descs:
                v = vrti._read_field(vablerti, desc, base, i)
                tgt = lltype.cast_pointer(desc.PTRTYPE, s)
                setattr(tgt, desc.fieldname, v)
                i = i + 1

        self.devirtualize = make, fill_into

    def _define_materialize(self):
        TYPE = self.TYPE
        descs = unrolling_iterable(self.fielddescs)
        
        def materialize(rgenop, boxes):
            s = lltype.malloc(TYPE)
            i = 0
            for desc in descs:
                v = rvalue.ll_getvalue(boxes[i], desc.RESTYPE)
                tgt = lltype.cast_pointer(desc.PTRTYPE, s)
                setattr(tgt, desc.fieldname, v)
                i = i + 1
            return rgenop.genconst(s)

        self.materialize = materialize
        
    def getfielddesc(self, name):
        try:
            return self.fielddesc_by_name[name]
        except KeyError:
            return self.firstsubstructdesc.getfielddesc(name)


    def factory(self):
        vstruct = self.VirtualStructCls(self)
        vstruct.content_boxes = [desc.makedefaultbox()
                                 for desc in self.fielddescs]
        box = rvalue.PtrRedBox(self.innermostdesc.ptrkind, known_nonzero=True)
        box.content = vstruct
        vstruct.ownbox = box
        return box


def create(jitstate, typedesc):
    return typedesc.factory()

def create_varsize(jitstate, contdesc, sizebox):
    gv_size = sizebox.getgenvar(jitstate)
    alloctoken = contdesc.varsizealloctoken
    genvar = jitstate.curbuilder.genop_malloc_varsize(alloctoken, gv_size)
    # XXX MemoryError checking
    return rvalue.PtrRedBox(contdesc.ptrkind, genvar, known_nonzero=True)


class VirtualizableStructTypeDesc(StructTypeDesc):

    VirtualStructCls = None # patched later with VirtualizableStruct

    _attrs_  =  """redirected_fielddescs
                   redirected
                   base_desc rti_desc access_desc
                   gv_access
                   touch_update
                   gv_access_is_null_ptr access_is_null_token
                   get_rti set_rti
                """.split()

    def __init__(self, hrtyper, TYPE):
        RGenOp = hrtyper.RGenOp
        StructTypeDesc.__init__(self, hrtyper, TYPE)
        ACCESS = self.TYPE.ACCESS
        redirected_fields = ACCESS.redirected_fields
        self.redirected_fielddescs = []
        self.redirected = {}
        i = 0
        for fielddesc in self.fielddescs:
            if fielddesc.fieldname in redirected_fields:
                self.redirected_fielddescs.append((fielddesc, i))
                self.redirected[i] = None
            i += 1
        self.base_desc = self.getfielddesc('vable_base')
        self.rti_desc = self.getfielddesc('vable_rti')
        self.access_desc = self.getfielddesc('vable_access')
        TOPPTR = self.access_desc.PTRTYPE
        self.s_structtype = annmodel.lltype_to_annotation(TOPPTR)

        annhelper = hrtyper.annhelper

        self.my_redirected_getsetters_untouched = {}
        self.my_redirected_getsetters_touched = {}        
        self.my_redirected_names = my_redirected_names = []
        j = -1
        for fielddesc, _  in self.redirected_fielddescs:
            j += 1
            if fielddesc.PTRTYPE != self.PTRTYPE:
                continue
            my_redirected_names.append(fielddesc.fieldname)
            self._define_getset_field_ptr(hrtyper, fielddesc, j)


        access_untouched = lltype.malloc(ACCESS, immortal=True)
        access_touched = lltype.malloc(ACCESS, immortal=True)
        self._fill_access('untouched', access_untouched)
        self._fill_access('touched',   access_touched)
        self.gv_access = RGenOp.constPrebuiltGlobal(access_untouched)

        self.touch_update = rvirtualizable.define_touch_update(TOPPTR,
                                self.redirected_fielddescs,
                                access_touched)

        self._define_collect_residual_args()

        self._define_access_is_null(hrtyper)


    def _define_virtual_desc(self):
        pass

    def _define_getset_field_ptr(self, hrtyper, fielddesc, j):
        annhelper = hrtyper.annhelper
        s_lltype = annmodel.lltype_to_annotation(fielddesc.RESTYPE)

        untouched = self.my_redirected_getsetters_untouched
        touched = self.my_redirected_getsetters_touched

        mkptr = annhelper.delayedfunction

        fnpairs = rvirtualizable.define_getset_field_ptrs(fielddesc, j)

        name = fielddesc.fieldname
        for getsetters, (get_field, set_field) in zip((untouched, touched),
                                                      fnpairs):

            get_field_ptr = mkptr(get_field, [self.s_structtype], s_lltype,
                                             needtype = True)
            set_field_ptr = mkptr(set_field, [self.s_structtype, s_lltype],
                                             annmodel.s_None, needtype=True)
            
            getsetters[name] = get_field_ptr, set_field_ptr

    def _fill_access(self, which, access):
        firstsubstructdesc = self.firstsubstructdesc
        if (firstsubstructdesc is not None and 
            isinstance(firstsubstructdesc, VirtualizableStructTypeDesc)):
            firstsubstructdesc._fill_access(which, access.parent)
            
        getsetters = getattr(self, 'my_redirected_getsetters_'+which)

        for name, (get_field_ptr, set_field_ptr) in getsetters.iteritems():
            setattr(access, 'get_'+name, get_field_ptr)
            setattr(access, 'set_'+name, set_field_ptr)
 
    def _define_collect_residual_args(self):
        my_redirected_names = unrolling_iterable(self.my_redirected_names)
        TOPPTR = self.access_desc.PTRTYPE

        if TOPPTR == self.PTRTYPE:
            _super_collect = None
        else:
            _super_collect = self.firstsubstructdesc._collect_residual_args

        def _collect_residual_args(v): 
            if _super_collect is None:
                assert not v.vable_access  # xxx need to use access ?
                t = ()
            else:
                t = _super_collect(v.super)
            for name in my_redirected_names:
                t = t + (getattr(v, name),)
            return t

        self._collect_residual_args = _collect_residual_args

        def collect_residual_args(v): 
            t = (v,) + _collect_residual_args(v)
            return t

        self.collect_residual_args = collect_residual_args


    def _define_access_is_null(self, hrtyper):
        RGenOp = hrtyper.RGenOp
        annhelper = hrtyper.annhelper        
        def access_is_null(struc):
            assert not struc.vable_access
        access_is_null_ptr = annhelper.delayedfunction(access_is_null,
                                                       [self.s_structtype],
                                                       annmodel.s_None,
                                                       needtype = True)
        self.gv_access_is_null_ptr = RGenOp.constPrebuiltGlobal(
                                              access_is_null_ptr)
        self.access_is_null_token =  RGenOp.sigToken(
                                   lltype.typeOf(access_is_null_ptr).TO)


    def factory(self):
        vstructbox = StructTypeDesc.factory(self)
        outsidebox = rvalue.PtrRedBox(self.innermostdesc.ptrkind,
                                      self.gv_null)
        content = vstructbox.content
        assert isinstance(content, VirtualizableStruct)
        content.content_boxes.append(outsidebox)             
        return vstructbox

# ____________________________________________________________

# XXX basic field descs for now
class FieldDesc(object):
    __metaclass__ = cachedtype
    _attrs_ = 'structdesc'
    
    allow_void = False
    virtualizable = False
    gv_default = None
    canbevirtual = False
    gcref = False
    fieldnonnull = False

    def __init__(self, hrtyper, PTRTYPE, RESTYPE):
        RGenOp = hrtyper.RGenOp
        self.PTRTYPE = PTRTYPE
        T = None
        if isinstance(RESTYPE, lltype.ContainerType):
            T = RESTYPE
            RESTYPE = lltype.Ptr(RESTYPE)
            self.fieldnonnull = True
        elif isinstance(RESTYPE, lltype.Ptr):
            T = RESTYPE.TO
            if hasattr(T, '_hints'):
                # xxx hack for simple recursive cases
                if not PTRTYPE.TO._hints.get('virtualizable', False):
                    self.virtualizable = T._hints.get('virtualizable', False)
            self.gcref = T._gckind == 'gc'
            if isinstance(T, lltype.ContainerType):
                if not T._is_varsize() or hasattr(T, 'll_newlist'):
                    self.canbevirtual = True
            else:
                T = None
            self.fieldnonnull = PTRTYPE.TO._hints.get('shouldntbenull', False)
        self.RESTYPE = RESTYPE
        self.ptrkind = RGenOp.kindToken(PTRTYPE)
        self.kind = RGenOp.kindToken(RESTYPE)
        if self.RESTYPE is not lltype.Void:
            self.gv_default = RGenOp.constPrebuiltGlobal(self.RESTYPE._defl())
        if RESTYPE is lltype.Void and self.allow_void:
            pass   # no redboxcls at all
        else:
            if self.virtualizable:
                self.structdesc = StructTypeDesc(hrtyper, T)
            self.redboxcls = rvalue.ll_redboxcls(RESTYPE)
            
        self.immutable = PTRTYPE.TO._hints.get('immutable', False)

    def _freeze_(self):
        return True

    def makedefaultbox(self):
        return self.redboxcls(self.kind, self.gv_default)
    
    def makebox(self, jitstate, gvar):
        if self.virtualizable:
            structbox = self.structdesc.factory()
            content = structbox.content
            assert isinstance(content, VirtualizableStruct)
            content.load_from(jitstate, gvar)
            return structbox
        box = self.redboxcls(self.kind, gvar)
        if self.fieldnonnull:
            assert isinstance(box, rvalue.PtrRedBox)
            box.known_nonzero = True
        return box

    
class NamedFieldDesc(FieldDesc):

    def __init__(self, hrtyper, PTRTYPE, name):
        FieldDesc.__init__(self, hrtyper, PTRTYPE, getattr(PTRTYPE.TO, name))
        T = self.PTRTYPE.TO
        self.fieldname = name
        self.fieldtoken = hrtyper.RGenOp.fieldToken(T, name)

    def compact_repr(self): # goes in ll helper names
        return "Fld_%s_in_%s" % (self.fieldname, self.PTRTYPE._short_name())

    def generate_get(self, jitstate, genvar):
        builder = jitstate.curbuilder
        gv_item = builder.genop_getfield(self.fieldtoken, genvar)
        return self.makebox(jitstate, gv_item)

    def generate_set(self, jitstate, genvar, gv_value):
        builder = jitstate.curbuilder
        builder.genop_setfield(self.fieldtoken, genvar, gv_value)

    def generate_getsubstruct(self, jitstate, genvar):
        builder = jitstate.curbuilder
        gv_sub = builder.genop_getsubstruct(self.fieldtoken, genvar)
        return self.makebox(jitstate, gv_sub)

class StructFieldDesc(NamedFieldDesc):

    def __init__(self, hrtyper, PTRTYPE, name, index):
        NamedFieldDesc.__init__(self, hrtyper, PTRTYPE, name)
        self.fieldindex = index

class ArrayFieldDesc(FieldDesc):
    allow_void = True

    def __init__(self, hrtyper, TYPE):
        assert isinstance(TYPE, lltype.Array)
        FieldDesc.__init__(self, hrtyper, lltype.Ptr(TYPE), TYPE.OF)
        RGenOp = hrtyper.RGenOp
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
    _attrs_ = "typedesc content_boxes ownbox".split()

    allowed_in_virtualizable = True
    
    def __init__(self, typedesc):
        self.typedesc = typedesc
        #self.content_boxes = ... set in factory()
        #self.ownbox = ... set in factory()

    def enter_block(self, incoming, memo):
        contmemo = memo.containers
        if self not in contmemo:
            contmemo[self] = None
            for box in self.content_boxes:
                box.enter_block(incoming, memo)

    def setforced(self, gv_forced):
        self.content_boxes = None
        self.ownbox.setgenvar_hint(gv_forced, known_nonzero=True)
        self.ownbox.content = None
        
    def force_runtime_container(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        boxes = self.content_boxes
        self.content_boxes = None
        if typedesc.materialize is not None:
            for box in boxes:
                if box is None or not box.is_constant():
                    break
            else:
                gv = typedesc.materialize(builder.rgenop, boxes)
                self.ownbox.setgenvar_hint(gv, known_nonzero=True)
                self.ownbox.content = None
                return
        debug_print(lltype.Void, "FORCE CONTAINER: "+ typedesc.TYPE._name)
        #debug_pdb(lltype.Void)
        genvar = builder.genop_malloc_fixedsize(typedesc.alloctoken)
        # force the box pointing to this VirtualStruct
        self.setforced(genvar)
        fielddescs = typedesc.fielddescs
        for i in range(len(fielddescs)):
            fielddesc = fielddescs[i]
            box = boxes[i]
            fielddesc.generate_set(jitstate, genvar, box.getgenvar(jitstate))

    def freeze(self, memo):
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = FrozenVirtualStruct(self.typedesc)
        frozens = [box.freeze(memo) for box in self.content_boxes]
        result.fz_content_boxes = frozens
        return result

    def copy(self, memo):
        typedesc = self.typedesc
        contmemo = memo.containers
        assert self not in contmemo     # contmemo no longer used
        result = contmemo[self] = typedesc.VirtualStructCls(typedesc)
        result.content_boxes = [box.copy(memo)
                                for box in self.content_boxes]
        result.ownbox = self.ownbox.copy(memo)
        return result

    def replace(self, memo):
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

    def make_rti(self, jitstate, memo):
        try:
            return memo.containers[self]
        except KeyError:
            pass
        typedesc = self.typedesc
        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        rgenop = jitstate.curbuilder.rgenop
        vrti = rvirtualizable.VirtualRTI(rgenop, bitmask)
        vrti.devirtualize = typedesc.devirtualize
        memo.containers[self] = vrti

        builder = jitstate.curbuilder
        place = builder.alloc_frame_place(typedesc.ptrkind)
        vrti.forced_place = place
        forced_box = rvalue.PtrRedBox(typedesc.ptrkind)
        memo.forced_boxes.append((forced_box, place))

        vars_gv = memo.framevars_gv
        varindexes = vrti.varindexes
        vrtis = vrti.vrtis
        j = -1
        for box in self.content_boxes:
            if box.genvar:
                varindexes.append(memo.frameindex)
                memo.frameindex += 1
                vars_gv.append(box.genvar)
            else:
                varindexes.append(j)
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable                
                vrtis.append(content.make_rti(jitstate, memo))
                j -= 1

        self.content_boxes.append(forced_box)
        return vrti

    def reshape(self, jitstate, shapemask, memo):
        if self in memo.containers:
            return
        typedesc = self.typedesc
        builder = jitstate.curbuilder        
        memo.containers[self] = None
        bitmask = 1<<memo.bitcount
        memo.bitcount += 1

        boxes = self.content_boxes
        outside_box = boxes.pop()
        if bitmask&shapemask:
            gv_forced = outside_box.genvar
            memo.forced.append((self, gv_forced))
            
        for box in boxes:
            if not box.genvar:
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.reshape(jitstate, shapemask, memo)

class VirtualizableStruct(VirtualStruct):
    
    def force_runtime_container(self, jitstate):
        assert 0

    def getgenvar(self, jitstate):
        typedesc = self.typedesc
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            assert isinstance(typedesc, VirtualizableStructTypeDesc)
            builder = jitstate.curbuilder
            gv_outside = builder.genop_malloc_fixedsize(typedesc.alloctoken)
            outsidebox = rvalue.PtrRedBox(self.content_boxes[-1].kind,
                                          gv_outside,
                                          known_nonzero = True)
            self.content_boxes[-1] = outsidebox
            jitstate.add_virtualizable(self.ownbox)
            #access_token = typedesc.access_desc.fieldtoken            
            #gv_access_null = typedesc.access_desc.gv_default
            #builder.genop_setfield(access_token, gv_outside, gv_access_null)
            # write all non-redirected fields
            boxes = self.content_boxes
            fielddescs = typedesc.fielddescs
            redirected = typedesc.redirected
            for i in range(len(fielddescs)):
                if i not in redirected:
                    fielddesc = fielddescs[i]
                    box = boxes[i]
                    fielddesc.generate_set(jitstate, gv_outside,
                                           box.getgenvar(jitstate))
        return gv_outside

    def store_back(self, jitstate):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        boxes = self.content_boxes
        gv_outside = boxes[-1].genvar
        for fielddesc, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            fielddesc.generate_set(jitstate, gv_outside,
                                   box.getgenvar(jitstate))

    def load_from(self, jitstate, gv_outside):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        # XXX missing check for gv_outside being NULL
        boxes = self.content_boxes
        boxes[-1] = rvalue.PtrRedBox(boxes[-1].kind,
                                     gv_outside,
                                     known_nonzero=True)
        builder = jitstate.curbuilder
        builder.genop_call(typedesc.access_is_null_token,
                           typedesc.gv_access_is_null_ptr,
                           [gv_outside])
        for fielddesc, i in typedesc.redirected_fielddescs:
            boxes[i] = fielddesc.generate_get(jitstate, gv_outside)
        jitstate.add_virtualizable(self.ownbox)

    def make_rti(self, jitstate, memo):
        typedesc = self.typedesc
        outsidebox = self.content_boxes[-1]
        gv_outside = outsidebox.genvar
        if gv_outside is typedesc.gv_null:
            return None
        try:
            return memo.containers[self]
        except KeyError:
            pass
        assert isinstance(typedesc, VirtualizableStructTypeDesc)        
        rgenop = jitstate.curbuilder.rgenop
        vable_rti = rvirtualizable.VirtualizableRTI(rgenop, 0)
        vable_rti.touch_update = typedesc.touch_update
        vable_rti.shape_place = jitstate.shape_place
        memo.containers[self] = vable_rti
        
        vars_gv = memo.framevars_gv
        varindexes = vable_rti.varindexes
        vrtis = vable_rti.vrtis
        boxes = self.content_boxes
        j = -1
        for _, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if box.genvar:
                varindexes.append(memo.frameindex)
                memo.frameindex += 1
                vars_gv.append(box.genvar)
            else:
                varindexes.append(j)
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                vrtis.append(content.make_rti(jitstate, memo))
                j -= 1

        nvirtual = -j-1
        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        memo.bitcount += nvirtual
        vable_rti.bitmask = bitmask
        return vable_rti

    def prepare_for_residual_call(self, jitstate, gv_base, vable_rti):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)        
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        base_desc = typedesc.base_desc
        base_token = base_desc.fieldtoken
        builder.genop_setfield(base_token, gv_outside, gv_base)
        vable_rti_ptr = cast_instance_to_base_ptr(vable_rti)
        gv_vable_rti = builder.rgenop.genconst(vable_rti_ptr)
        rti_token = typedesc.rti_desc.fieldtoken
        builder.genop_setfield(rti_token, gv_outside, gv_vable_rti)
        access_token = typedesc.access_desc.fieldtoken
        builder.genop_setfield(access_token, gv_outside, typedesc.gv_access)

    def check_forced_after_residual_call(self, jitstate):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            return
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        access_token = typedesc.access_desc.fieldtoken            
        gv_access_null = typedesc.access_desc.gv_default
        builder.genop_setfield(access_token, gv_outside, gv_access_null)


    def reshape(self, jitstate, shapemask, memo):
        typedesc = self.typedesc
        builder = jitstate.curbuilder
        gv_outside = self.content_boxes[-1].genvar
        if gv_outside is typedesc.gv_null:
            return
        if self in memo.containers:
            return
        memo.containers[self] = None
        assert isinstance(typedesc, VirtualizableStructTypeDesc)

        boxes = self.content_boxes
        nvirtual = 0
        for _, i in typedesc.redirected_fielddescs:
            box = boxes[i]
            if not box.genvar:
                nvirtual += 1
                assert isinstance(box, rvalue.PtrRedBox)
                content = box.content
                assert content.allowed_in_virtualizable
                content.reshape(jitstate, shapemask, memo)

        bitmask = 1 << memo.bitcount
        memo.bitcount += 1
        memo.bitcount += nvirtual
        if shapemask&bitmask:
            vmask = bitmask
            for fielddesc, i in typedesc.redirected_fielddescs:
                box = boxes[i]
                if not box.genvar:
                    vmask = vmask<<1
                    if not (shapemask&vmask):
                        continue
                boxes[i] = fielddesc.generate_get(jitstate, gv_outside)

    def op_getfield(self, jitstate, fielddesc):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        gv_outside = self.content_boxes[-1].genvar
        fieldindex = fielddesc.fieldindex
        if (gv_outside is typedesc.gv_null or
            fieldindex in typedesc.redirected):
            return self.content_boxes[fieldindex]
        else:
            gv_ptr = self.getgenvar(jitstate)
            box = fielddesc.generate_get(jitstate, gv_ptr)
            return box
        
    def op_setfield(self, jitstate, fielddesc, valuebox):
        typedesc = self.typedesc
        assert isinstance(typedesc, VirtualizableStructTypeDesc)
        fieldindex = fielddesc.fieldindex
        gv_outside = self.content_boxes[-1].genvar
        if (gv_outside is typedesc.gv_null or
            fieldindex in typedesc.redirected):
            self.content_boxes[fielddesc.fieldindex] = valuebox
        else:
            gv_ptr = self.getgenvar(jitstate)
            fielddesc.generate_set(jitstate, gv_ptr,
                                   valuebox.getgenvar(jitstate))
            

# patching VirtualStructCls
StructTypeDesc.VirtualStructCls = VirtualStruct
VirtualizableStructTypeDesc.VirtualStructCls = VirtualizableStruct


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
