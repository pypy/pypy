RINGBUFFER_SIZE          = 8192
RINGBUFFER_ENTRY_MAXSIZE = 16
RINGBUFFER_OVERSIZE      = RINGBUFFER_SIZE + RINGBUFFER_ENTRY_MAXSIZE

ringbuffer_decl = """
; 8208=8192+16 in the next line because the last one (16 bytes maxsize) might
; start at 8190 for instance. [RINGBUFFER_SIZE + RINGBUFFER_ENTRY_MAXSIZE]

%%exception_ringbuffer = internal global [%s x sbyte] zeroinitializer
%%exception_ringbuffer_index = internal global uint 0
""" % (RINGBUFFER_SIZE + RINGBUFFER_ENTRY_MAXSIZE)

ringbuffer_code = '''
internal fastcc sbyte* %%malloc_exception(uint %%nbytes) {
    %%cond = setle uint %%nbytes, %d
    br bool %%cond, label %%then, label %%else

then:
    %%tmp.3 = load uint* %%exception_ringbuffer_index
    %%tmp.4 = getelementptr [%d x sbyte]* %%exception_ringbuffer, int 0, uint %%tmp.3
    %%tmp.6 = add uint %%tmp.3, %%nbytes
    %%tmp.7 = and uint %%tmp.6, %d
    store uint %%tmp.7, uint* %%exception_ringbuffer_index
    ret sbyte* %%tmp.4

else:
    %%tmp.8  = call ccc sbyte* %%pypy_malloc(uint %%nbytes)
    ret sbyte* %%tmp.8
}
''' % (RINGBUFFER_ENTRY_MAXSIZE, RINGBUFFER_OVERSIZE, RINGBUFFER_SIZE - 1)

import sys
if sys.maxint != 2**31-1: #XXX need to move the ringbuffer code to another level anyway
	ringbuffer_decl = ringbuffer_code = ''

invokeunwind_code = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    %%result = invoke %(cconv)s %(returntype)s%%%(entrypointname)s to label %%no_exception except label %%exception

no_exception:
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    ret %(returntype)s %%result

exception:
    ret %(noresult)s
}

ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

internal fastcc void %%unwind() {
    unwind
}
'''

explicit_code = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = call %(cconv)s %(returntype)s%%%(entrypointname)s
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%exc    = seteq %%RPYTHON_EXCEPTION_VTABLE* %%tmp, null
    br bool %%exc, label %%no_exception, label %%exception

no_exception:
    ret %(returntype)s %%result

exception:
    ret %(noresult)s
}

ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

internal fastcc void %%unwind() {
    ret void
}
'''
