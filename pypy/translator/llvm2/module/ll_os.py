extdeclarations = """
;ll_os.py
declare ccc int %dup(int)
declare ccc void %close(int)
declare ccc int %open(sbyte*, int, int)
declare ccc int %write(int, sbyte*, int)
declare ccc int %read(int, sbyte*, int)
declare ccc sbyte* %strncpy(sbyte*, sbyte*, int)
declare ccc int %isatty(int)
declare ccc int %fstat(int, int*)
"""

extfunctions = {}

extfunctions["%ll_os_dup"] = ((), """
internal fastcc int %ll_os_dup(int %fd) {
    %ret = call ccc int %dup(int %fd)
    ret int %ret
}

""")

extfunctions["%ll_os_close"] = ((), """
internal fastcc void %ll_os_close(int %fd) {
    call ccc void %close(int %fd)
    ret void
}

""")

extfunctions["%ll_os_open"] = (("%cast",), """
internal fastcc int %ll_os_open(%structtype.rpy_string* %structstring, int %flag, int %mode) {
    %dest  = call fastcc sbyte* %cast(%structtype.rpy_string* %structstring)
    %fd    = call ccc    int    %open(sbyte* %dest, int %flag, int %mode)
    ret int %fd 
}

""")

extfunctions["%ll_os_write"] = (("%cast",), """
internal fastcc int %ll_os_write(int %fd, %structtype.rpy_string* %structstring) {
    %reallengthptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 
    %dest          = call fastcc sbyte* %cast(%structtype.rpy_string* %structstring)
    %byteswritten  = call ccc    int    %write(int %fd, sbyte* %dest, int %reallength)
    ret int %byteswritten
}

""")

extfunctions["%ll_read_into"] = ((), """
internal fastcc int %ll_read_into(int %fd, %structtype.rpy_string* %structstring) {
    %reallengthptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 

    %destptr   = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 1
    %dest      = cast [0 x sbyte]* %destptr to sbyte*

    %bytesread = call ccc int %read(int %fd, sbyte* %dest, int %reallength)
    ret int %bytesread
}

""")

extfunctions["%ll_os_isatty"] = ((), """
internal fastcc bool %ll_os_isatty(int %fd) {
    %ret = call ccc int %isatty(int %fd)
    %ret.bool = cast int %ret to bool
    ret bool %ret.bool
}

""")

extfunctions["%ll_os_fstat"] = ((), """
internal fastcc %structtype.tuple10* %ll_os_fstat(int %fd) {
    ;%st = alloca int, uint 32
    ;%error = call ccc int %fstat(int %fd, int* %st)
    ;;TODO XXX if error: raise exception
    ;;%ret = %ll_stat_result__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed(
    ;%ret = alloca %structtype.tuple10   ;ERROR
    ;store int %s
    ;ret %structtype.tuple10* %ret
    ret %structtype.tuple10* null
}

""")

extfunctions["%ll_os_ftruncate"] = ((), """
internal fastcc void %ll_os_ftruncate(int %x, int %y) {
    ; XXX: TODO: ll_os_ftruncate
    ret void
}
""")

extfunctions["%ll_os_lseek"] = ((), """
internal fastcc int %ll_os_lseek(int %x, int %y, int %z) {
    ; XXX: TODO: ll_os_lseek
    ret int 0
}
""")

extfunctions["%ll_os_stat"] = ((), """
internal fastcc %structtype.tuple10* %ll_os_stat(%structtype.rpy_string* %s) {
    ; XXX: TODO: ll_os_stat
    ret %structtype.tuple10* null
}
""")

extfunctions["%ll_strtod_formatd"] = ((), """
internal fastcc %structtype.rpy_string* %ll_strtod_formatd(%structtype.rpy_string* %s, double %x) {
    ; XXX: TODO: ll_strtod_formatd
    ret %structtype.rpy_string* null
}
""")

extfunctions["%"] = ((), """
internal fastcc double %ll_strtod_parts_to_float(%structtype.rpy_string* s0, %structtype.rpy_string* s1, %structtype.rpy_string* s2, %structtype.rpy_string* s3) {
    ; XXX: TODO: ll_strtod_parts_to_float
    ret double 0.0
}
""")
