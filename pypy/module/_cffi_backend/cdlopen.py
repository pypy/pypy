from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import specialize

from pypy.module._cffi_backend.parse_c_type import (
    _CFFI_OPCODE_T, GLOBAL_S, CDL_INTCONST_S,
    ll_set_cdl_realize_global_int)
from pypy.module._cffi_backend.realize_c_type import getop
from pypy.module._cffi_backend import cffi_opcode


class StringDecoder:
    def __init__(self, ffi, string):
        self.ffi = ffi
        self.string = string
        self.pos = 0

    def next_4bytes(self):
        pos = self.pos
        src = ord(self.string[pos])
        if src >= 0x80:
            src -= 0x100
        src = ((src << 24) |
               (ord(self.string[pos + 1]) << 16) |
               (ord(self.string[pos + 2]) << 8 ) |
               (ord(self.string[pos + 3])      ))
        self.pos = pos + 4
        return src

    def next_opcode(self):
        return rffi.cast(_CFFI_OPCODE_T, self.next_4bytes())

    def next_name(self):
        frm = self.pos
        i = self.string.find('\x00', frm)
        if i < 0:
            i = len(self.string)
        pos = i + 1
        p = rffi.str2charp(self.string[frm : i])
        self.ffi._finalizer.free_mems.append(p)
        return p


def allocate(ffi, nbytes):
    p = lltype.malloc(rffi.CCHARP.TO, nbytes, flavor='raw', zero=True)
    ffi._finalizer.free_mems.append(p)
    return p

@specialize.arg(1)
def allocate_array(ffi, OF, nitems):
    p = allocate(ffi, nitems * rffi.sizeof(OF))
    return rffi.cast(rffi.CArrayPtr(OF), p)


def ffiobj_init(ffi, module_name, version, types, w_globals,
                w_struct_unions, w_enums, w_typenames, w_includes):
    space = ffi.space

    if types:
        # unpack a string of 4-byte entries into an array of _cffi_opcode_t
        n = len(types) // 4
        ntypes = allocate_array(ffi, _CFFI_OPCODE_T, n)
        decoder = StringDecoder(ffi, types)
        for i in range(n):
            ntypes[i] = decoder.next_opcode()
        ffi.ctxobj.ctx.c_types = ntypes
        rffi.setintfield(ffi.ctxobj.ctx, 'c_num_types', n)
        ffi.cached_types = [None] * n

    if w_globals is not None:
        globals_w = space.fixedview(w_globals)
        n = len(globals_w) // 2
        size = n * rffi.sizeof(GLOBAL_S) + n * rffi.sizeof(CDL_INTCONST_S)
        size = llmemory.raw_malloc_usage(size)
        p = allocate(ffi, size)
        nglobs = rffi.cast(rffi.CArrayPtr(GLOBAL_S), p)
        p = rffi.ptradd(p, llmemory.raw_malloc_usage(n * rffi.sizeof(GLOBAL_S)))
        nintconsts = rffi.cast(rffi.CArrayPtr(CDL_INTCONST_S), p)
        for i in range(n):
            decoder = StringDecoder(ffi, space.str_w(globals_w[i * 2]))
            nglobs[i].c_type_op = decoder.next_opcode()
            nglobs[i].c_name = decoder.next_name()
            op = getop(nglobs[i].c_type_op)
            if op == cffi_opcode.OP_CONSTANT_INT or op == cffi_opcode.OP_ENUM:
                w_integer = globals_w[i * 2 + 1]
                ll_set_cdl_realize_global_int(nglobs[i])
                bigint = space.bigint_w(w_integer)
                ullvalue = bigint.ulonglongmask()
                rffi.setintfield(nintconsts[i], 'neg', int(bigint.sign <= 0))
                rffi.setintfield(nintconsts[i], 'value', ullvalue)
        ffi.ctxobj.ctx.c_globals = nglobs
        rffi.setintfield(ffi.ctxobj.ctx, 'c_num_globals', n)

    # ...
