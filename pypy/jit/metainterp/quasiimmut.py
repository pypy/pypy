from pypy.rpython.rclass import IR_QUASI_IMMUTABLE
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance


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
