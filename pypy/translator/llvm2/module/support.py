extdeclarations = ""

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

for exc in "ZeroDivisionError OverflowError ValueError".split():
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

for func_inst in "floordiv_zer:div mod_zer:rem".split():
    func, inst = func_inst.split(':')
    for type_ in "int uint".split():
        extfunctions["%%%(type_)s_%(func)s" % locals()] = (("%__prepare_ZeroDivisionError",), """
fastcc %(type_)s %%%(type_)s_%(func)s(%(type_)s %%x, %(type_)s %%y) {
    %%cond = seteq %(type_)s %%y, 0
    br bool %%cond, label %%is_0, label %%is_not_0
is_not_0:
    %%z = %(inst)s %(type_)s %%x, %%y
    ret %(type_)s %%z
is_0:
    call fastcc void %%__prepare_ZeroDivisionError()
    unwind
}

""" % locals())

#XXX TODO
#src/int.h:#define OP_INT_FLOORDIV_OVF_ZER(x,y,r,err) \
#src/int.h:#define OP_INT_MOD_OVF_ZER(x,y,r,err) 
