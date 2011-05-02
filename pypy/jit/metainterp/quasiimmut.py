import weakref
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

def get_current_qmut_instance(cpu, gcref, mutatefielddescr):
    """Returns the current QuasiImmut instance in the field,
    possibly creating one.
    """
    qmut_gcref = cpu.bh_getfield_gc_r(gcref, mutatefielddescr)
    if qmut_gcref:
        qmut = QuasiImmut.show(cpu, qmut_gcref)
    else:
        qmut = QuasiImmut(cpu)
        cpu.bh_setfield_gc_r(gcref, mutatefielddescr, qmut.hide())
    return qmut

def make_invalidation_function(STRUCT, mutatefieldname):
    #
    def _invalidate_now(p):
        qmut_ptr = getattr(p, mutatefieldname)
        setattr(p, mutatefieldname, lltype.nullptr(rclass.OBJECT))
        qmut = cast_base_ptr_to_instance(QuasiImmut, qmut_ptr)
        qmut.invalidate()
    _invalidate_now._dont_inline_ = True
    #
    def invalidation(p):
        if getattr(p, mutatefieldname):
            _invalidate_now(p)
    #
    return invalidation

def do_force_quasi_immutable(cpu, p, mutatefielddescr):
    qmut_ref = cpu.bh_getfield_gc_r(p, mutatefielddescr)
    if qmut_ref:
        cpu.bh_setfield_gc_r(p, mutatefielddescr, cpu.ts.NULLREF)
        qmut_ptr = lltype.cast_opaque_ptr(rclass.OBJECTPTR, qmut_ref)
        qmut = cast_base_ptr_to_instance(QuasiImmut, qmut_ptr)
        qmut.invalidate()


class QuasiImmut(object):
    llopaque = True
    
    def __init__(self, cpu):
        self.cpu = cpu
        # list of weakrefs to the LoopTokens that must be invalidated if
        # this value ever changes
        self.looptokens_wrefs = []
        self.compress_limit = 30

    def hide(self):
        qmut_ptr = self.cpu.ts.cast_instance_to_base_ref(self)
        return self.cpu.ts.cast_to_ref(qmut_ptr)

    @staticmethod
    def show(cpu, qmut_gcref):
        qmut_ptr = cpu.ts.cast_to_baseclass(qmut_gcref)
        return cast_base_ptr_to_instance(QuasiImmut, qmut_ptr)

    def register_loop_token(self, wref_looptoken):
        if len(self.looptokens_wrefs) > self.compress_limit:
            self.compress_looptokens_list()
        self.looptokens_wrefs.append(wref_looptoken)

    def compress_looptokens_list(self):
        self.looptokens_wrefs = [wref for wref in self.looptokens_wrefs
                                      if wref() is not None]
        self.compress_limit = (len(self.looptokens_wrefs) + 15) * 2

    def invalidate(self):
        # When this is called, all the loops that we record become
        # invalid: all GUARD_NOT_INVALIDATED in these loops (and
        # in attached bridges) must now fail.
        wrefs = self.looptokens_wrefs
        self.looptokens_wrefs = []
        for wref in wrefs:
            looptoken = wref()
            if looptoken is not None:
                self.cpu.invalidate_loop(looptoken)


class QuasiImmutDescr(AbstractDescr):
    structbox = None

    def __init__(self, cpu, structbox, fielddescr, mutatefielddescr):
        self.cpu = cpu
        self.structbox = structbox
        self.fielddescr = fielddescr
        self.mutatefielddescr = mutatefielddescr
        gcref = structbox.getref_base()
        self.qmut = get_current_qmut_instance(cpu, gcref, mutatefielddescr)
        self.constantfieldbox = self.get_current_constant_fieldvalue()

    def get_current_constant_fieldvalue(self):
        from pypy.jit.metainterp import executor
        from pypy.jit.metainterp.resoperation import rop
        fieldbox = executor.execute(self.cpu, None, rop.GETFIELD_GC,
                                    self.fielddescr, self.structbox)
        return fieldbox.constbox()

    def is_still_valid(self):
        assert self.structbox is not None
        cpu = self.cpu
        gcref = self.structbox.getref_base()
        qmut = get_current_qmut_instance(cpu, gcref, self.mutatefielddescr)
        if qmut is not self.qmut:
            return False
        else:
            currentbox = self.get_current_constant_fieldvalue()
            assert self.constantfieldbox.same_constant(currentbox)
            return True
