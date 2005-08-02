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
