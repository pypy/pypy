
from pypy.jit.metainterp import history
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.annlowlevel import llhelper

class VirtualizableDesc(history.AbstractValue):
    hash = 0

    def __init__(self, cpu, TOPSTRUCT):
        "NOT_RPYTHON"
        initialize_virtualizable(cpu, TOPSTRUCT.access)
        self.vable_base = cpu.fielddescrof(TOPSTRUCT, 'vable_base')
        self.vable_rti  = cpu.fielddescrof(TOPSTRUCT, 'vable_rti')
        self.c_vable_base = history.ConstInt(self.vable_base)
        self.c_vable_rti  = history.ConstInt(self.vable_rti)

def initialize_virtualizable(cpu, access):
    if not hasattr(cpu, '_seen_virtualizables'):
        cpu._seen_virtualizables = {}
    if access in cpu._seen_virtualizables:
        return
    cpu._seen_virtualizables[access] = True
    for fieldname in access.redirected_fields:
        initialize_vable_field(cpu, access, fieldname)
    for subaccess in access.subaccessors:
        initialize_virtualizable(cpu, subaccess)
    if access.parent is not None:
        initialize_virtualizable(cpu, access.parent)

def initialize_vable_field(cpu, access, fieldname):
    FIELDTYPE = getattr(access.STRUCT, fieldname)
    if FIELDTYPE is lltype.Void:
        return
    type = history.getkind_num(cpu, FIELDTYPE)
    ofs = cpu.fielddescrof(access.STRUCT, fieldname)
    getset = access.getsets[fieldname]

    def getter(instanceptr):
        rti = instanceptr.vable_rti
        if we_are_translated():
            rti = cast_base_ptr_to_instance(VirtualizableRTI, rti)
        instanceptr = lltype.cast_opaque_ptr(llmemory.GCREF, instanceptr)
        box = rti.get_field(instanceptr, ofs, type)
        if type == 'ptr':
            return box.getptr(RESTYPE)
        else:
            return lltype.cast_primitive(RESTYPE, box.getint())

    def setter(instanceptr, value):
        rti = instanceptr.vable_rti
        if we_are_translated():
            rti = cast_base_ptr_to_instance(VirtualizableRTI, rti)
        instanceadr = lltype.cast_opaque_ptr(llmemory.GCREF, instanceptr)
        if type == 'ptr':
            valuebox = BoxPtr(llmemory.cast_ptr_to_adr(value))
        else:
            valuebox = BoxInt(lltype.cast_primitive(lltype.Signed, value))
        rti.set_field(instanceadr, ofs, type, valuebox)

    GETSET = lltype.typeOf(getset).TO
    RESTYPE = GETSET.get.TO.RESULT
    if cpu.translate_support_code:
        mixlevelann = cpu.mixlevelann
        getset.get = mixlevelann.delayedfunction(getter,
                         [lltype_to_annotation(t) for t in GETSET.get.TO.ARGS],
                         lltype_to_annotation(GETSET.get.TO.RESULT),
                                             needtype=True)
        getset.set = mixlevelann.delayedfunction(setter,
                         [lltype_to_annotation(t) for t in GETSET.set.TO.ARGS],
                         lltype_to_annotation(GETSET.set.TO.RESULT),
                                             needtype=True)
    else:
        # for testing: when the cpu and the metainterp are not translated
        getset.get = llhelper(GETSET.get, getter)
        getset.set = llhelper(GETSET.set, setter)
