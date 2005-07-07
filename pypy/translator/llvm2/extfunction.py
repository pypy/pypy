extdeclarations =  """; External declarations


; XXX these int's might need to be long's on 64 bit CPU's :(

declare int %time(int*) ;void* actually
declare int %clock()
declare void %sleep(int)
declare int %open(sbyte*, int)
declare sbyte* %strncpy(sbyte*, sbyte*, int)

%st.rpy_string.0 = type {int, {int, [0 x sbyte]}}

; End of external declarations

"""

extfunctions = """; Helper function to convert LLVM <-> C types

sbyte* %cast(%st.rpy_string.0* %structstring) {
    %reallengthptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 0
    %reallength = load int* %reallengthptr 
    %length = add int %reallength, 1
    %ulength = cast int %length to uint 
    %dest = malloc sbyte, uint %ulength     ;XXX should actually call GC_malloc when available!
    
    %source1ptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 1
    %source1 = cast [0 x sbyte]* %source1ptr to sbyte* 
    %dummy = call sbyte* %strncpy(sbyte* %dest, sbyte* %source1, int %reallength) 
    
    %zeropos1 = cast sbyte* %dest to int 
    %zeropos2 = add int %zeropos1, %reallength 
    %zerodest = cast int %zeropos2 to sbyte* 
    store sbyte 0, sbyte* %zerodest 

    ret sbyte* %dest    ;XXX alloca freed at end of function. this will crash!
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

int %ll_os_open(%st.rpy_string.0* %structstring, int %mode) {
    %dest = call sbyte* %cast(%st.rpy_string.0* %structstring)
    %fd   = call int    %open(sbyte* %dest, int %mode)
    free sbyte* %dest
    ret int %fd 
}

; End of external functions
"""
