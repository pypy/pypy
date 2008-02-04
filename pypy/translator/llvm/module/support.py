extfunctions = """
define internal double @pypyop_float_abs(double %x) {
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

define internal i32 @pypyop_int_abs(i32 %x) {
block0:
    %cond1 = icmp sge i32 %x, 0
    br i1 %cond1, label %return_block, label %block1
block1:
    %x2 = sub i32 0, %x
    br label %return_block
return_block:
    %result = phi i32 [%x, %block0], [%x2, %block1]
    ret i32 %result
}

define internal i64 @pypyop_llong_abs(i64 %x) {
block0:
    %cond1 = icmp sge i64 %x, 0
    br i1 %cond1, label %return_block, label %block1
block1:
    %x2 = sub i64 0, %x
    br label %return_block
return_block:
    %result = phi i64 [%x, %block0], [%x2, %block1]
    ret i64 %result
}

declare void @llvm.gcroot(i8**, i8*) nounwind
declare i8* @llvm.frameaddress(i32) nounwind

@__gcmapstart = external constant i8
@__gcmapend   = external constant i8
"""

