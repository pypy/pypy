"""
This file is mostly here for testing.  Usually, transform.py will transform
the getfields (etc) that occur in the graphs directly into stm_getfields,
which are operations that are recognized by the C backend.  See funcgen.py
which contains similar logic, which is run by the C backend.
"""
import sys
from pypy.rpython.lltypesystem import lltype, rffi, rclass
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.stm import _rffi_stm
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rlib.rarithmetic import r_uint, r_ulonglong
from pypy.rlib import longlong2float
from pypy.rlib.objectmodel import specialize
from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance

size_of_voidp = rffi.sizeof(rffi.VOIDP)
assert size_of_voidp & (size_of_voidp - 1) == 0

assert sys.byteorder == 'little'   # xxx fix here, in funcgen.py, and in et.c


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
        if fieldsize == size_of_voidp:
            res = _rffi_stm.stm_read_word(p)
        elif fieldsize == 8:    # 32-bit only: read a 64-bit field
            res0 = r_uint(_rffi_stm.stm_read_word(p))
            res1 = r_uint(_rffi_stm.stm_read_word(rffi.ptradd(p, 1)))
            res = (r_ulonglong(res1) << 32) | res0
        else:
            raise NotImplementedError(fieldsize)
        if FIELD == lltype.Float:
            return longlong2float.longlong2float(rffi.cast(rffi.LONGLONG, res))
    else:
        assert misalignment + fieldsize <= size_of_voidp
        res = _rffi_stm.stm_read_word(p)
        res = res >> (misalignment * 8)
    if FIELD == lltype.SingleFloat:
        return longlong2float.uint2singlefloat(rffi.cast(rffi.UINT, res))
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
    if FIELD == lltype.SingleFloat:
        newvalue = longlong2float.singlefloat2uint(newvalue)
    if fieldsize >= size_of_voidp:
        assert misalignment == 0
        if FIELD == lltype.Float:
            newvalue = longlong2float.float2longlong(newvalue)
        if fieldsize == size_of_voidp:
            _rffi_stm.stm_write_word(p, rffi.cast(lltype.Signed, newvalue))
        elif fieldsize == 8:    # 32-bit only: write a 64-bit field
            _rffi_stm.stm_write_word(p, rffi.cast(lltype.Signed, newvalue))
            p = rffi.ptradd(p, 1)
            newvalue = rffi.cast(lltype.SignedLongLong, newvalue) >> 32
            _rffi_stm.stm_write_word(p, rffi.cast(lltype.Signed, newvalue))
        else:
            raise NotImplementedError(fieldsize)
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

def stm_getarrayitem(arrayptr, index):
    "NOT_RPYTHON"
    raise NotImplementedError("sorry")

##def stm_setarrayitem(arrayptr, index, value):
##    "NOT_RPYTHON"
##    raise NotImplementedError("sorry")

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
        hop.exception_cannot_occur()
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
        hop.exception_cannot_occur()
        hop.genop('stm_setfield', [v_structptr, c_fieldname, v_newvalue])


class ExtEntry(ExtRegistryEntry):
    _about_ = stm_getarrayitem

    def compute_result_annotation(self, s_arrayptr, s_index):
        from pypy.tool.pairtype import pair
        return pair(s_arrayptr, s_index).getitem()

    def specialize_call(self, hop):
        r_arrayptr = hop.args_r[0]
        v_arrayptr, v_index = hop.inputargs(r_arrayptr, lltype.Signed)
        hop.exception_cannot_occur()
        return hop.genop('stm_getarrayitem', [v_arrayptr, v_index],
                         resulttype = hop.r_result)


##class ExtEntry(ExtRegistryEntry):
##    _about_ = (begin_transaction, commit_transaction,
##               begin_inevitable_transaction, transaction_boundary)

##    def compute_result_annotation(self):
##        return None

##    def specialize_call(self, hop):
##        hop.exception_cannot_occur()
##        hop.genop("stm_" + self.instance.__name__, [])
