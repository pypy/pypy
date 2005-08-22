extdeclarations = """
declare ccc double %pow(double, double)
declare ccc double %fmod(double, double)
declare ccc INT %puts(sbyte*)
declare ccc INT %strlen(sbyte*)
declare ccc INT %strcmp(sbyte*, sbyte*)
declare ccc sbyte* %memset(sbyte*, INT, UINT)

%__print_debug_info         = internal global bool false
%__print_debug_info_option  = internal constant [19 x sbyte] c"--print-debug-info\\00"
"""


extfunctions = {}

extfunctions["%__debug"] = ((), """
internal fastcc void %__debug([12 x sbyte]* %msg12) {
    %cond = load bool* %__print_debug_info
    br bool %cond, label %print_it, label %do_nothing

do_nothing:
    ret void
    
print_it:
    %msg = getelementptr [12 x sbyte]* %msg12, int 0, int 0
    call int %puts(sbyte* %msg)
    ret void
}

""")

extfunctions["%cast"] = (("%string_to_RPyString",), """
internal fastcc sbyte* %cast(%RPyString* %structstring) {
    %source1ptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte*
    ret sbyte* %source1
}

""")

extfunctions["%string_to_RPyString"] = ((), """
internal fastcc %RPyString* %string_to_RPyString(sbyte* %s) {
    %len       = call ccc INT %strlen(sbyte* %s)
    %rpy       = call fastcc %RPyString* %RPyString_New__Signed(int %len)
    %rpystrptr = getelementptr %RPyString* %rpy, int 0, uint 1, uint 1
    %rpystr    = cast [0 x sbyte]* %rpystrptr to sbyte*

    call ccc sbyte* %strncpy(sbyte* %rpystr, sbyte* %s, INT %len)

    ret %RPyString* %rpy
}

""")

#abs functions
extfunctions["%int_abs"] = ((), """
internal fastcc INT %int_abs(INT %x) {
block0:
    %cond1 = setge INT %x, 0
    br bool %cond1, label %return_block, label %block1
block1:
    %x2 = sub INT 0, %x
    br label %return_block
return_block:
    %result = phi INT [%x, %block0], [%x2, %block1]
    ret INT %result
}

""")

extfunctions["%float_abs"] = ((), """
internal fastcc double %float_abs(double %x) {
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

""")


#prepare exceptions
for exc in "ZeroDivisionError OverflowError ValueError".split():    #_ZER _OVF _VAL
    extfunctions["%%__prepare_%(exc)s" % locals()] = ((), """
internal fastcc void %%__prepare_%(exc)s() {
    %%exception_value = call fastcc %%RPYTHON_EXCEPTION* %%instantiate_%(exc)s()
    %%tmp             = getelementptr %%RPYTHON_EXCEPTION* %%exception_value, int 0, uint 0
    %%exception_type  = load %%RPYTHON_EXCEPTION_VTABLE** %%tmp
    store %%RPYTHON_EXCEPTION_VTABLE* %%exception_type, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    store %%RPYTHON_EXCEPTION* %%exception_value, %%RPYTHON_EXCEPTION** %%last_exception_value
    ret void
}
""" % locals())


#error-checking-code

zer_test = """
    %%cond = seteq %s %%y, 0
    br bool %%cond, label %%is_0, label %%is_not_0
is_0:
    call fastcc void %%__prepare_ZeroDivisionError()
    unwind

is_not_0:
"""
int_zer_test    = zer_test % ('int',)
double_zer_test = zer_test % ('double',)


#overflow: normal operation, ...if ((x) >= 0 || (x) != -(x)) OK else _OVF()
#note: XXX this hardcoded int32 minint value is used because of a pre llvm1.6 bug!

int_ovf_test = """
    %cond2 = setne INT %x, -2147483648
    br bool %cond2, label %return_block, label %ovf
ovf:
    call fastcc void %__prepare_OverflowError()
    unwind
"""


#binary with ZeroDivisionError only

for func_inst in "floordiv_zer:div mod_zer:rem".split():
    func, inst = func_inst.split(':')
    for prefix_type_ in "int:INT uint:UINT".split():
        prefix, type_ = prefix_type_.split(':')
        type_zer_test = zer_test % type_
        extfunctions["%%%(prefix)s_%(func)s" % locals()] = (("%__prepare_ZeroDivisionError",), """
internal fastcc %(type_)s %%%(prefix)s_%(func)s(%(type_)s %%x, %(type_)s %%y) {
    %(type_zer_test)s
    %%z = %(inst)s %(type_)s %%x, %%y
    ret %(type_)s %%z
}

""" % locals())


#unary with OverflowError only

extfunctions["%int_neg_ovf"] = (("%__prepare_OverflowError",), """
internal fastcc INT %%int_neg_ovf(INT %%x) {
block1:
    %%x2 = sub INT 0, %%x
    %(int_ovf_test)s
return_block:
    ret INT %%x2
}
""" % locals())

extfunctions["%int_abs_ovf"] = (("%__prepare_OverflowError",), """
internal fastcc INT %%int_abs_ovf(INT %%x) {
block0:
    %%cond1 = setge INT %%x, 0
    br bool %%cond1, label %%return_block, label %%block1
block1:
    %%x2 = sub INT 0, %%x
    %(int_ovf_test)s
return_block:
    %%result = phi INT [%%x, %%block0], [%%x2, %%block1]
    ret INT %%result
}
""" % locals())


#binary with OverflowError only

extfunctions["%int_add_ovf"] = (("%__prepare_OverflowError",), """
internal fastcc INT %%int_add_ovf(INT %%x, INT %%y) {
    %%t = add INT %%x, %%y
    %(int_ovf_test)s
return_block:
    ; XXX: TEST int_add_ovf checking
    ret INT %%t
}
""" % locals())

extfunctions["%int_sub_ovf"] = (("%__prepare_OverflowError",), """
internal fastcc INT %%int_sub_ovf(INT %%x, INT %%y) {
    %%t = sub INT %%x, %%y
    %(int_ovf_test)s
return_block:
    ; XXX: TEST int_sub_ovf checking
    ret INT %%t
}
""" % locals())

extfunctions["%int_mul_ovf"] = (("%__prepare_OverflowError",), """
internal fastcc INT %%int_mul_ovf(INT %%x, INT %%y) {
    %%t = mul INT %%x, %%y
    %(int_ovf_test)s
return_block:
    ; XXX: TEST int_mul_ovf checking
    ret INT %%t
}
""" % locals())


#binary with OverflowError and ValueError

extfunctions["%int_lshift_ovf_val"] = (("%__prepare_OverflowError","%__prepare_ValueError"), """
internal fastcc INT %%int_lshift_ovf_val(INT %%x, INT %%y) {
    %%yu = cast INT %%y to ubyte
    %%t = shl INT %%x, ubyte %%yu
    %(int_ovf_test)s
return_block:
    ; XXX: TODO int_lshift_ovf_val checking VAL
    ret INT %%t
}
""" % locals())


#binary with OverflowError and ZeroDivisionError

extfunctions["%int_floordiv_ovf_zer"] = (("%__prepare_OverflowError","%__prepare_ZeroDivisionError"), """
internal fastcc INT %%int_floordiv_ovf_zer(INT %%x, INT %%y) {
    %(int_zer_test)s
    %%t = div INT %%x, %%y
    %(int_ovf_test)s
return_block:
    ; XXX: TEST int_floordiv_ovf_zer checking
    ret INT %%t
}
""" % locals())

extfunctions["%int_mod_ovf_zer"] = (("%__prepare_OverflowError","%__prepare_ZeroDivisionError"), """
internal fastcc INT %%int_mod_ovf_zer(INT %%x, INT %%y) {
    %(int_zer_test)s
    %%t = rem INT %%x, %%y
    %(int_ovf_test)s
return_block:
    ; XXX: TEST int_mod_ovf_zer checking
    ret INT %%t
}
""" % locals())

extfunctions["%main"] = (("%string_to_RPyString"), """
INT %main(INT %argc, sbyte** %argv) {
entry:
    %pypy_argv = call fastcc %RPyListOfString* %ll_newlist__listPtrConst_Signed.2(INT 0)
    br label %no_exit

no_exit:
    %indvar = phi UINT [ %indvar.next, %next_arg ], [ 0, %entry ]
    %i.0.0 = cast UINT %indvar to INT
    %tmp.8 = getelementptr sbyte** %argv, UINT %indvar
    %tmp.9 = load sbyte** %tmp.8

    %t    = getelementptr [19 x sbyte]* %__print_debug_info_option, int 0, int 0
    %res  = call ccc INT %strcmp(sbyte* %tmp.9, sbyte* %t)
    %cond = seteq INT %res, 0
    br bool %cond, label %debugging, label %not_debugging

debugging:
    store bool true, bool* %__print_debug_info
    br label %next_arg

not_debugging:
    %rpy = call fastcc %RPyString* %string_to_RPyString(sbyte* %tmp.9)
    call fastcc void %ll_append__listPtr_rpy_stringPtr(%RPyListOfString* %pypy_argv, %RPyString* %rpy)
    br label %next_arg

next_arg:
    %inc = add INT %i.0.0, 1
    %tmp.2 = setlt INT %inc, %argc
    %indvar.next = add UINT %indvar, 1
    br bool %tmp.2, label %no_exit, label %loopexit

loopexit:

    %ret  = call fastcc INT %entry_point(%structtype.list* %pypy_argv)
    ret INT %ret
}
""")
