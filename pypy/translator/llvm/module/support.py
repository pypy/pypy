
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

extfunctions = {}

extfunctions["%RPyString_AsString"] = """
internal fastcc sbyte* %RPyString_AsString(%RPyString* %structstring) {
    %source1ptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte*
    ret sbyte* %source1
}

"""

extfunctions["%RPyString_Size"] = """
internal fastcc int %RPyString_Size(%RPyString* %structstring) {
    %sizeptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %size = load int* %sizeptr
    ret int %size
}

"""

extfunctions["%RPyString_FromString"] = """
internal fastcc %RPyString* %RPyString_FromString(sbyte* %s) {
    %lenu      = call ccc uint %strlen(sbyte* %s)
    %len       = cast uint %lenu to int
    %rpy       = call fastcc %RPyString* %pypy_RPyString_New__Signed(int %len)
    %rpystrptr = getelementptr %RPyString* %rpy, int 0, uint 1, uint 1
    %rpystr    = cast [0 x sbyte]* %rpystrptr to sbyte*

    call ccc void %llvm.memcpy(sbyte* %rpystr, sbyte* %s, uint %lenu, uint 0)

    ret %RPyString* %rpy
}

"""

# abs functions
extfunctions["%pypyop_int_abs"] = """
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

"""

extfunctions["%pypyop_float_abs"] = """
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


# prepare exceptions
for exc in "ZeroDivisionError OverflowError ValueError".split():
    extfunctions["%%prepare_%(exc)s" % locals()] = """
internal fastcc void %%prepare_%(exc)s() {
    %%exception_value = cast %%structtype.%(exc)s* %%structinstance.%(exc)s to %%RPYTHON_EXCEPTION*
    %%tmp             = getelementptr %%RPYTHON_EXCEPTION* %%exception_value, int 0, uint 0
    %%exception_type  = load %%RPYTHON_EXCEPTION_VTABLE** %%tmp
    store %%RPYTHON_EXCEPTION_VTABLE* %%exception_type, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    store %%RPYTHON_EXCEPTION* %%exception_value, %%RPYTHON_EXCEPTION** %%last_exception_value
    ret void
}
""" % locals()


# prepare and raise exceptions (%msg not used right now!)
for exc in "IOError ZeroDivisionError " \
           "OverflowError ValueError RuntimeError".split():
    extfunctions["%%raisePyExc_%(exc)s" % locals()] = """
internal fastcc void %%raisePyExc_%(exc)s(sbyte* %%msg) {
    %%exception_value = cast %%structtype.%(exc)s* %%structinstance.%(exc)s to %%RPYTHON_EXCEPTION*
    %%tmp             = getelementptr %%RPYTHON_EXCEPTION* %%exception_value, int 0, uint 0
    %%exception_type  = load %%RPYTHON_EXCEPTION_VTABLE** %%tmp
    store %%RPYTHON_EXCEPTION_VTABLE* %%exception_type, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    store %%RPYTHON_EXCEPTION* %%exception_value, %%RPYTHON_EXCEPTION** %%last_exception_value
    call fastcc void %%unwind()
    ret void
}
""" % locals()

# main functions to be moved to genexterns
# XXX rewrite these in C
entry_functions = {}

entry_functions["main_noargs"] = """
int %main(int %argc, sbyte** %argv) {
    store int 0, int* %GC_all_interior_pointers
    %ret  = call fastcc int %pypy_main_noargs()
    ret int %ret
}
"""

entry_functions["entry_point"] = """
int %main(int %argc, sbyte** %argv) {
entry:
    store int 0, int* %GC_all_interior_pointers
    %pypy_argv = call fastcc %RPyListOfString* %pypy__RPyListOfString_New__Signed(int %argc)
    br label %no_exit

no_exit:
    %indvar = phi uint [ %indvar.next, %no_exit ], [ 0, %entry ]
    %i.0.0 = cast uint %indvar to int
    %tmp.8 = getelementptr sbyte** %argv, uint %indvar
    %tmp.9 = load sbyte** %tmp.8
    %rpy = call fastcc %RPyString* %RPyString_FromString(sbyte* %tmp.9)
    call fastcc void %pypy__RPyListOfString_SetItem__listPtr_Signed_rpy_stringPtr(%RPyListOfString* %pypy_argv, int %i.0.0, %RPyString* %rpy)
    %inc = add int %i.0.0, 1
    %tmp.2 = setlt int %inc, %argc
    %indvar.next = add uint %indvar, 1
    br bool %tmp.2, label %no_exit, label %loopexit

loopexit:
    %ret  = call fastcc int %pypy_entry_point(%RPyListOfString* %pypy_argv)
    ret int %ret
}
"""
