extdeclarations = """
declare ccc double %pow(double, double)
declare ccc double %fmod(double, double)
"""


extfunctions = {}

extfunctions["%cast"] = ((), """
fastcc sbyte* %cast(%structtype.rpy_string* %structstring) {
    %reallengthptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 0
    %reallength = load int* %reallengthptr
    %length = add int %reallength, 1
    %ulength = cast int %length to uint
    %dest = call fastcc sbyte* %gc_malloc_atomic(uint %ulength)

    %source1ptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte*
    %dummy = call ccc sbyte* %strncpy(sbyte* %dest, sbyte* %source1, int %reallength)

    %zeropos1 = cast sbyte* %dest to int
    %zeropos2 = add int %zeropos1, %reallength
    %zerodest = cast int %zeropos2 to sbyte*
    store sbyte 0, sbyte* %zerodest

    ret sbyte* %dest
}

""")


#abs functions
extfunctions["%int_abs"] = ((), """
fastcc int %int_abs(int %x) {
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

""")

extfunctions["%float_abs"] = ((), """
fastcc double %float_abs(double %x) {
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
fastcc void %%__prepare_%(exc)s() {
    %%exception_value = call fastcc %%structtype.object* %%instantiate_%(exc)s()
    %%tmp             = getelementptr %%structtype.object* %%exception_value, int 0, uint 0
    %%exception_type  = load %%structtype.object_vtable** %%tmp
    store %%structtype.object_vtable* %%exception_type, %%structtype.object_vtable** %%last_exception_type
    store %%structtype.object* %%exception_value, %%structtype.object** %%last_exception_value
    ret void
}
""" % locals())


#binary with ZeroDivisionError only
for func_inst in "floordiv_zer:div mod_zer:rem".split():
    func, inst = func_inst.split(':')
    for type_ in "int uint".split():
        extfunctions["%%%(type_)s_%(func)s" % locals()] = (("%__prepare_ZeroDivisionError",), """
fastcc %(type_)s %%%(type_)s_%(func)s(%(type_)s %%x, %(type_)s %%y) {

    ;zerodiv test
    %%cond = seteq %(type_)s %%y, 0
    br bool %%cond, label %%is_0, label %%is_not_0
is_0:
    call fastcc void %%__prepare_ZeroDivisionError()
    unwind
    
is_not_0:
    %%z = %(inst)s %(type_)s %%x, %%y
    ret %(type_)s %%z
}

""" % locals())


int_ovf_test = """
    %cond2 = setne int %x, -2147483648  ;-sys.maxint-1
    br bool %cond2, label %return_block, label %ovf
ovf:
    call fastcc void %__prepare_OverflowError()
    unwind
"""

#unary with OverflowError only

extfunctions["%int_neg_ovf"] = (("%__prepare_OverflowError",), """
fastcc int %%int_neg_ovf(int %%x) {
block1:
    %%x2 = sub int 0, %%x
    %(int_ovf_test)s
return_block:
    ret int %%x2
}
""" % locals())

extfunctions["%int_abs_ovf"] = (("%__prepare_OverflowError",), """
fastcc int %%int_abs_ovf(int %%x) {
block0:
    %%cond1 = setge int %%x, 0
    br bool %%cond1, label %%return_block, label %%block1
block1:
    %%x2 = sub int 0, %%x
    %(int_ovf_test)s
return_block:
    %%result = phi int [%%x, %%block0], [%%x2, %%block1]
    ret int %%result
}
""" % locals())


#XXX TODO

#extfunctions["%float_pow"] = ((), """
#fastcc double %float_pow(double %x, double %y) {
#    ; XXX ERROR float_pow exception raising not implemented
#    %r = call ccc double %pow(double %x, double %y)
#    ret double %r
#}
#
#""")
#
#extfunctions["%float_mod"] = ((), """
#fastcc double %float_mod(double %x, double %y) {
#    ; XXX ERROR float_mod exception raising not implemented
#    %r = call ccc double %fmod(double %x, double %y)
#    ret double %r
#}
#
#""")
#
#for func in 'float_abs float_sub float_add float_mul float_div'.split():
#    extfunctions["%" + func] = ((), """
#fastcc double %%%(func)s(double %%x, double %%y) {
#    ; XXX ERROR %(func)s exception raising not implemented
#    ret double 0.0
#}
#
#""" % locals())
#
#for func in 'int_abs int_sub int_add int_mul int_div int_mod int_add_ovf int_sub_ovf int_mul_ovf int_floordiv_ovf int_mod_ovf int_floordiv_ovf_zer int_mod_ovf_zer int_lshift_ovf int_lshift_ovf_val int_rshift_val int_lshift_val'.split():
#    extfunctions["%" + func] = ((), """
#fastcc int %%%(func)s(int %%x, int %%y) {
#    ; XXX ERROR %(func)s exception raising not implemented
#    ret int 0
#}
#
#""" % locals())


#XXX TODO

#overflow: normal operation, ...if ((x) >= 0 || (x) != -(x)) ok else _OVF()

#binary with overflow
#define OP_INT_ADD_OVF(x,y,r,err) \
#define OP_INT_SUB_OVF(x,y,r,err) \
#define OP_INT_MUL_OVF(x,y,r,err) \
#define OP_INT_MUL_OVF(x,y,r,err) \
#define OP_INT_FLOORDIV_OVF(x,y,r,err) \
#define OP_INT_MOD_OVF(x,y,r,err) \

#binary with overflow and zerodiv
#define OP_INT_FLOORDIV_OVF_ZER(x,y,r,err) \
#define OP_INT_MOD_OVF_ZER(x,y,r,err) \

#shift
#define OP_INT_LSHIFT_OVF(x,y,r,err) \
#define OP_INT_LSHIFT_OVF_VAL(x,y,r,err) \
#define OP_INT_RSHIFT_VAL(x,y,r,err) \
#define OP_INT_LSHIFT_VAL(x,y,r,err) \


#DONE

#binary with zerodivisionerror only
#define OP_INT_FLOORDIV_ZER(x,y,r,err) \
#define OP_UINT_FLOORDIV_ZER(x,y,r,err) \
#define OP_INT_MOD_ZER(x,y,r,err) \
#define OP_UINT_MOD_ZER(x,y,r,err) \

#unary with overflow only
#define OP_INT_ABS_OVF(x,r,err) \   untested
#define OP_INT_NEG_OVF(x,r,err) \   untested

