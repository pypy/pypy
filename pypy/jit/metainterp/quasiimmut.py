from pypy.rpython.rclass import IR_QUASI_IMMUTABLE
from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.jit.metainterp.history import AbstractDescr


def is_quasi_immutable(STRUCT, fieldname):
    imm_fields = STRUCT._hints.get('immutable_fields')
    return (imm_fields is not None and
            imm_fields.fields.get(fieldname) is IR_QUASI_IMMUTABLE)

def get_mutate_field_name(fieldname):
    if fieldname.startswith('inst_'):    # lltype
        return 'mutate_' + fieldname[5:]
    elif fieldname.startswith('o'):      # ootype
        return 'mutate_' + fieldname[1:]
    else:
        raise AssertionError(fieldname)

def get_current_mutate_instance(cpu, gcref, mutatefielddescr):
    """Returns the current SlowMutate instance in the field,
    possibly creating one.
    """
    mutate_gcref = cpu.bh_getfield_gc_r(gcref, mutatefielddescr)
    if mutate_gcref:
        mutate = SlowMutate.show(cpu, mutate_gcref)
    else:
        mutate = SlowMutate()
        cpu.bh_setfield_gc_r(gcref, mutatefielddescr, mutate.hide(cpu))
    return mutate

def make_invalidation_function(STRUCT, mutatefieldname):
    #
    def _invalidate_now(p):
        mutate_ptr = getattr(p, mutatefieldname)
        setattr(p, mutatefieldname, lltype.nullptr(rclass.OBJECT))
        mutate = cast_base_ptr_to_instance(SlowMutate, mutate_ptr)
        mutate.invalidate()
    _invalidate_now._dont_inline_ = True
    #
    def invalidation(p):
        if getattr(p, mutatefieldname):
            _invalidate_now(p)
    #
    return invalidation


class SlowMutate(object):
    def __init__(self):
        pass

    def hide(self, cpu):
        mutate_ptr = cpu.ts.cast_instance_to_base_ref(self)
        return cpu.ts.cast_to_ref(mutate_ptr)

    @staticmethod
    def show(cpu, mutate_gcref):
        mutate_ptr = cpu.ts.cast_to_baseclass(mutate_gcref)
        return cast_base_ptr_to_instance(SlowMutate, mutate_ptr)

    def invalidate(self):
        pass    # XXX


class SlowMutateDescr(AbstractDescr):
    def __init__(self, cpu, structbox, fielddescr, mutatefielddescr):
        self.cpu = cpu
        self.structbox = structbox
        self.fielddescr = fielddescr
        self.mutatefielddescr = mutatefielddescr
        gcref = structbox.getref_base()
        self.mutate = get_current_mutate_instance(cpu, gcref, mutatefielddescr)
        self.constantfieldbox = self.get_current_constant_fieldvalue()

    def get_current_constant_fieldvalue(self):
        from pypy.jit.metainterp import executor
        from pypy.jit.metainterp.resoperation import rop
        fieldbox = executor.execute(self.cpu, None, rop.GETFIELD_GC,
                                    self.fielddescr, self.structbox)
        return fieldbox.constbox()

    def is_still_valid(self):
        gcref = self.structbox.getref_base()
        curmut = get_current_mutate_instance(self.cpu, gcref,
                                             self.mutatefielddescr)
        if curmut is not self.mutate:
            return False
        else:
            currentbox = self.get_current_constant_fieldvalue()
            assert self.constantfieldbox.same_constant(currentbox)
            return True
