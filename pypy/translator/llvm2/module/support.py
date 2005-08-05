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

extfunctions["%__prepare_ZeroDivisionError"] = ((), """
fastcc void %__prepare_ZeroDivisionError() {

    %exception_value = call fastcc %structtype.object* %instantiate_ZeroDivisionError()

    %tmp             = getelementptr %structtype.object* %exception_value, int 0, uint 0
    %exception_type  = load %structtype.object_vtable** %tmp
    store %structtype.object_vtable* %exception_type, %structtype.object_vtable** %last_exception_type
    store %structtype.object* %exception_value, %structtype.object** %last_exception_value

    ret void
}

""")

extfunctions["%int_floordiv_zer"] = (("%__prepare_ZeroDivisionError",), """
fastcc int %int_floordiv_zer(int %x, int %y) {
    %cond = seteq int %y, 0
    br bool %cond, label %is_0, label %is_not_0
is_not_0:
    %z = add int %x, %y
    ret int %z
is_0:
    call fastcc void %__prepare_ZeroDivisionError()
    unwind
}

""")

#XXX could use template here
extfunctions["%uint_floordiv_zer"] = (("%__prepare_ZeroDivisionError",), """
fastcc uint %uint_floordiv_zer(uint %x, uint %y) {
    %cond = seteq uint %y, 0
    br bool %cond, label %is_0, label %is_not_0
is_not_0:
    %z = add uint %x, %y
    ret uint %z
is_0:
    call fastcc void %__prepare_ZeroDivisionError()
    unwind
}

""")

#src/int.h:#define OP_INT_FLOORDIV_ZER(x,y,r,err) \     done
#src/int.h:#define OP_UINT_FLOORDIV_ZER(x,y,r,err) \    done
#src/int.h:#define OP_INT_FLOORDIV_OVF_ZER(x,y,r,err) \
#src/int.h:#define OP_INT_MOD_ZER(x,y,r,err) \
#src/int.h:#define OP_UINT_MOD_ZER(x,y,r,err) \
#src/int.h:#define OP_INT_MOD_OVF_ZER(x,y,r,err) 
