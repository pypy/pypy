from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.stm import _rffi_stm
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant


def stm_getfield(structptr, fieldname):
    p = lltype.direct_fieldptr(structptr, fieldname)
    p = rffi.cast(rffi.VOIDPP, p)
    res = _rffi_stm.stm_read_word(p)
    return rffi.cast(lltype.Signed, res)

def stm_setfield(structptr, fieldname, newvalue):
    p = lltype.direct_fieldptr(structptr, fieldname)
    p = rffi.cast(rffi.VOIDPP, p)
    pval = rffi.cast(rffi.VOIDP, newvalue)
    _rffi_stm.stm_write_word(p, pval)


# ____________________________________________________________

class ExtEntry(ExtRegistryEntry):
    _about_ = stm_getfield

    def compute_result_annotation(self, s_structptr, s_fieldname):
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        r_structptr = hop.args_r[0]
        v_structptr = hop.inputarg(r_structptr, arg=0)
        fieldname = hop.args_v[1].value
        c_fieldname = hop.inputconst(lltype.Void, fieldname)
        return hop.genop('stm_getfield', [v_structptr, c_fieldname],
                         resulttype = lltype.Signed)


class ExtEntry(ExtRegistryEntry):
    _about_ = stm_setfield

    def compute_result_annotation(self, s_structptr, s_fieldname, s_newvalue):
        return None

    def specialize_call(self, hop):
        r_structptr = hop.args_r[0]
        v_structptr = hop.inputarg(r_structptr, arg=0)
        fieldname = hop.args_v[1].value
        v_newvalue = hop.inputarg(hop.args_r[2], arg=2)
        c_fieldname = hop.inputconst(lltype.Void, fieldname)
        hop.genop('stm_setfield', [v_structptr, c_fieldname, v_newvalue])
