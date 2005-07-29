extdeclarations = """
;ll_os.py
declare int %dup(int)
declare void %close(int)
declare int %open(sbyte*, int, int)
declare int %write(int, sbyte*, int)
declare int %read(int, sbyte*, int)
declare sbyte* %strncpy(sbyte*, sbyte*, int)
"""

extfunctions = {}

extfunctions["%ll_os_dup"] = ((), """
int %ll_os_dup(int %fd) {
    %ret = call int %dup(int %fd)
    ret int %ret
}

""")

extfunctions["%ll_os_close"] = ((), """
void %ll_os_close(int %fd) {
    call void %close(int %fd)
    ret void
}

""")

extfunctions["%ll_os_open"] = (("%cast",), """
int %ll_os_open(%structtype.rpy_string* %structstring, int %flag, int %mode) {
    %dest  = call sbyte* %cast(%structtype.rpy_string* %structstring)
    %fd    = call int    %open(sbyte* %dest, int %flag, int %mode)
    ret int %fd 
}

""")

extfunctions["%ll_os_write"] = (("%cast",), """
int %ll_os_write(int %fd, %structtype.rpy_string* %structstring) {
    %reallengthptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 
    %dest          = call sbyte* %cast(%structtype.rpy_string* %structstring)
    %byteswritten  = call int    %write(int %fd, sbyte* %dest, int %reallength)
    ret int %byteswritten
}

""")

extfunctions["%ll_read_into"] = ((), """
int %ll_read_into(int %fd, %structtype.rpy_string* %structstring) {
    %reallengthptr = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 

    %destptr   = getelementptr %structtype.rpy_string* %structstring, int 0, uint 1, uint 1
    %dest      = cast [0 x sbyte]* %destptr to sbyte*

    %bytesread = call int %read(int %fd, sbyte* %dest, int %reallength)
    ret int %bytesread
}

""")
