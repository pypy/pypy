
extdeclarations = """
%last_exception_type  = internal global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = internal global %RPYTHON_EXCEPTION* null

; XXXX This in a translation option - move to exception.py!
;8208=8192+16 in the next line because the last one (16 bytes maxsize) might start at 8190 for instance.
%exception_ringbuffer = internal global [8208 x sbyte] zeroinitializer
%exception_ringbuffer_index = internal global uint 0

declare ccc uint %strlen(sbyte*)
declare ccc void %llvm.memset(sbyte*, ubyte, uint, uint)
declare ccc void %llvm.memcpy(sbyte*, sbyte*, uint, uint)
"""

extfunctions = """
internal fastcc sbyte* %RPyString_AsString(%RPyString* %structstring) {
    %source1ptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte*
    ret sbyte* %source1
}

internal fastcc int %RPyString_Size(%RPyString* %structstring) {
    %sizeptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %size = load int* %sizeptr
    ret int %size
}

internal fastcc int %RPyExceptionOccurred() {
    %tmp.0 = load %RPYTHON_EXCEPTION_VTABLE** %last_exception_type
    %bool_res = setne %RPYTHON_EXCEPTION_VTABLE* %tmp.0, null
    %res = cast bool %bool_res to int
    ret int %res
}

internal fastcc %RPyString* %RPyString_FromString(sbyte* %s) {
    %lenu      = call ccc uint %strlen(sbyte* %s)
    %len       = cast uint %lenu to int
    %rpy       = call fastcc %RPyString* %pypy_RPyString_New__Signed(int %len)
    %rpystrptr = getelementptr %RPyString* %rpy, int 0, uint 1, uint 1
    %rpystr    = cast [0 x sbyte]* %rpystrptr to sbyte*

    call ccc void %llvm.memcpy(sbyte* %rpystr, sbyte* %s, uint %lenu, uint 0)

    ret %RPyString* %rpy
}

internal fastcc int %pypyop_int_abs(int %x) {
block0:
    %cond1 = setge int %x, 0
    br bool %cond1, label %return_block, label %block1
block1:
    %x2 = sub int 0, %x
    br label %return_block
return_block:
    %result = phi int [%x, %block0], [%x2, %block1]
    ret int %result
}


internal fastcc double %pypyop_float_abs(double %x) {
block0:
    %cond1 = setge double %x, 0.0
    br bool %cond1, label %return_block, label %block1
block1:
    %x2 = sub double 0.0, %x
    br label %return_block
return_block:
    %result = phi double [%x, %block0], [%x2, %block1]
    ret double %result
}

"""

def write_raise_exc(c_name, exc_repr, codewriter):

    l = """
internal fastcc void %%raise%s(sbyte* %%msg) {
    %%exception_value = cast %s to %%RPYTHON_EXCEPTION*
    %%tmp             = getelementptr %%RPYTHON_EXCEPTION* %%exception_value, int 0, uint 0
    %%exception_type  = load %%RPYTHON_EXCEPTION_VTABLE** %%tmp
    store %%RPYTHON_EXCEPTION_VTABLE* %%exception_type, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    store %%RPYTHON_EXCEPTION* %%exception_value, %%RPYTHON_EXCEPTION** %%last_exception_value
    call fastcc void %%unwind()
    ret void
}
""" % (c_name, exc_repr)
    codewriter.append(l)

