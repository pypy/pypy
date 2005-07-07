extdeclarations =  """; External declarations


; XXX these int's might need to be long's on 64 bit CPU's :(

declare sbyte* %gc_malloc(uint)
declare sbyte* %gc_malloc_atomic(uint)
declare int %time(int*) ;void* actually
declare int %clock()
declare void %sleep(int)
declare int %open(sbyte*, int, int)
declare int %write(int, sbyte*, int)
declare int %read(int, sbyte*, int)
declare sbyte* %strncpy(sbyte*, sbyte*, int)

%st.rpy_string.0 = type {int, {int, [0 x sbyte]}}

; End of external declarations

"""

gc_boehm = """; Using Boehm GC

declare sbyte* %GC_malloc(uint)
declare sbyte* %GC_malloc_atomic(uint)

sbyte* %gc_malloc(uint %n) {
    %ptr = call sbyte* %GC_malloc(uint %n)
    ret sbyte* %ptr
}

sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = call sbyte* %GC_malloc_atomic(uint %n)
    ret sbyte* %ptr
}

"""

gc_disabled = """; Using no GC

sbyte* %gc_malloc(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

"""

extfunctions = """; Helper function to convert LLVM <-> C types

sbyte* %cast(%st.rpy_string.0* %structstring) {
    %reallengthptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 0
    %reallength = load int* %reallengthptr 
    %length = add int %reallength, 1
    %ulength = cast int %length to uint 
    %dest = call sbyte* %gc_malloc_atomic(uint %ulength)

    %source1ptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte* 
    %dummy = call sbyte* %strncpy(sbyte* %dest, sbyte* %source1, int %reallength) 

    %zeropos1 = cast sbyte* %dest to int 
    %zeropos2 = add int %zeropos1, %reallength 
    %zerodest = cast int %zeropos2 to sbyte* 
    store sbyte 0, sbyte* %zerodest 

    ret sbyte* %dest
}

; Wrapper functions that call external (C) functions

double %ll_time_time() {
    %v0 = call int %time(int* null)
    %v1 = cast int %v0 to double
    ret double %v1
}

double %ll_time_clock() {
    %v0 = call int %clock()
    %v1 = cast int %v0 to double
    ; XXX how to get at the proper division constant per platform? 
    %v2 = div double %v1, 1000000.0    ;CLOCKS_PER_SEC accrdoing to single unix spec
    ret double %v2
}

void %ll_time_sleep(double %f) {
    %i = cast double %f to int
    call void %sleep(int %i)
    ret void
}

int %ll_os_open(%st.rpy_string.0* %structstring, int %pythonmode) {
    %flags = cast int %pythonmode to int
    %mode  = cast int 384         to int    ;S_IRUSR=256, S_IWUSR=128
    %dest  = call sbyte* %cast(%st.rpy_string.0* %structstring)
    %fd    = call int    %open(sbyte* %dest, int %flags, int %mode)
    ret int %fd 
}

int %ll_os_write(int %fd, %st.rpy_string.0* %structstring) {
    %reallengthptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 
    %dest          = call sbyte* %cast(%st.rpy_string.0* %structstring)
    %byteswritten  = call int    %write(int %fd, sbyte* %dest, int %reallength)
    ret int %byteswritten
}

%st.rpy_string.0* %ll_os_read(int %fd, int %buffersize) {
    ;TODO: read(fd, buffersize) -> string
    ret %st.rpy_string.0* null
}

; End of external functions
"""
