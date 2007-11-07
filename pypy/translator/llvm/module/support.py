extdeclarations = """
declare ccc i32 @strlen(i8*)
"""

extfunctions = """
define internal CC %RPyString* @RPyString_FromString(i8* %s) {
    %len       = call ccc i32 @strlen(i8* %s)
    %rpy       = call CC %RPyString* @pypy_RPyString_New__Signed(i32 %len)
    %rpystrptr = getelementptr %RPyString* %rpy, i32 0, i32 1, i32 1
    %rpystr    = bitcast [0 x i8]* %rpystrptr to i8*

    call ccc void @llvm.memcpyPOSTFIX(i8* %rpystr, i8* %s, WORD %len, WORD 0)

    ret %RPyString* %rpy
}

define internal CC i8* @RPyString_AsString(%RPyString* %structstring) {
    %source1ptr = getelementptr %RPyString* %structstring, i32 0, i32 1, i32 1
    %source1 = bitcast [0 x i8]* %source1ptr to i8*
    ret i8* %source1
}

define internal CC WORD @RPyString_Size(%RPyString* %structstring) {
    %sizeptr = getelementptr %RPyString* %structstring, i32 0, i32 1, i32 0
    %size = load WORD* %sizeptr
    ret WORD %size
}

define internal CC double @pypyop_float_abs(double %x) {
block0:
    %cond1 = fcmp ugt double %x, 0.0
    br i1 %cond1, label %return_block, label %block1
block1:
    %x2 = sub double 0.0, %x
    br label %return_block
return_block:
    %result = phi double [%x, %block0], [%x2, %block1]
    ret double %result
}

"""
"""
internal CC WORD %pypyop_int_abs(WORD %x) {
block0:
    %cond1 = setge WORD %x, 0
    br bool %cond1, label %return_block, label %block1
block1:
    %x2 = sub WORD 0, %x
    br label %return_block
return_block:
    %result = phi WORD [%x, %block0], [%x2, %block1]
    ret WORD %result
}

internal CC long %pypyop_llong_abs(long %x) {
block0:
    %cond1 = setge long %x, 0
    br bool %cond1, label %return_block, label %block1
block1:
    %x2 = sub long 0, %x
    br label %return_block
return_block:
    %result = phi long [%x, %block0], [%x2, %block1]
    ret long %result
}

"""

extfunctions_standalone = """
"""
from sys import maxint
if maxint != 2**31-1:
    extfunctions_standalone += """
internal CC int %pypy_entry_point(%RPyListOfString* %argv) {
    %result = call CC long %pypy_entry_point(%RPyListOfString* %argv)
    %tmp = cast long %result to int
    ret int %tmp
}

"""

def write_raise_exc(c_name, exc_repr, codewriter):
    l = """
define internal CC void @raise%s(i8* %%msg) {
    ;%%exception_value = cast %s to %%RPYTHON_EXCEPTION*
    ret void
}
""" % (c_name, exc_repr)
    codewriter.write_lines(l, patch=True)

