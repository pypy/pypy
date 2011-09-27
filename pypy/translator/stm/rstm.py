import sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.stm import _rffi_stm
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant

size_of_voidp = rffi.sizeof(rffi.VOIDP)
assert size_of_voidp & (size_of_voidp - 1) == 0

assert sys.byteorder == 'little'   # xxx fix here and in funcgen.py


def stm_getfield(structptr, fieldname):
    "NOT_RPYTHON"
    STRUCT = lltype.typeOf(structptr).TO
    FIELD = getattr(STRUCT, fieldname)
    p = lltype.direct_fieldptr(structptr, fieldname)
    p = rffi.cast(lltype.Signed, p)
    misalignment = p & (size_of_voidp - 1)
    fieldsize = rffi.sizeof(FIELD)
    p = rffi.cast(_rffi_stm.SignedP, p - misalignment)
    if fieldsize >= size_of_voidp:
        assert misalignment == 0
        assert fieldsize == size_of_voidp   # XXX
        res = _rffi_stm.stm_read_word(p)
    else:
        assert misalignment + fieldsize <= size_of_voidp
        res = _rffi_stm.stm_read_word(p)
        res = res >> (misalignment * 8)
    return rffi.cast(FIELD, res)

def stm_setfield(structptr, fieldname, newvalue):
    "NOT_RPYTHON"
    STRUCT = lltype.typeOf(structptr).TO
    FIELD = getattr(STRUCT, fieldname)
    p = lltype.direct_fieldptr(structptr, fieldname)
    p = rffi.cast(lltype.Signed, p)
    misalignment = p & (size_of_voidp - 1)
    fieldsize = rffi.sizeof(FIELD)
    #print 'setfield %x size %d:' % (p, fieldsize),
    p = rffi.cast(_rffi_stm.SignedP, p - misalignment)
    if fieldsize >= size_of_voidp:
        assert misalignment == 0
        assert fieldsize == size_of_voidp   # XXX
        _rffi_stm.stm_write_word(p, rffi.cast(lltype.Signed, newvalue))
        #print 'ok'
    else:
        # bah, must read the complete word in order to modify only a part
        assert misalignment + fieldsize <= size_of_voidp
        val = rffi.cast(lltype.Signed, newvalue)
        val = val << (misalignment * 8)
        word = _rffi_stm.stm_read_word(p)
        mask = ((1 << (fieldsize * 8)) - 1) << (misalignment * 8)
        val = (val & mask) | (word & ~mask)
        #print 'getting %x, mask=%x, replacing with %x' % (word, mask, val)
        _rffi_stm.stm_write_word(p, val)

# ____________________________________________________________


class ExtEntry(ExtRegistryEntry):
    _about_ = stm_getfield

    def compute_result_annotation(self, s_structptr, s_fieldname):
        return s_structptr.getattr(s_fieldname)

    def specialize_call(self, hop):
        r_structptr = hop.args_r[0]
        v_structptr = hop.inputarg(r_structptr, arg=0)
        fieldname = hop.args_v[1].value
        c_fieldname = hop.inputconst(lltype.Void, fieldname)
        return hop.genop('stm_getfield', [v_structptr, c_fieldname],
                         resulttype = hop.r_result)


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
