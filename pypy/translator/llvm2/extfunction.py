extdeclarations = """; External declarations

; XXX these int's might need to be long's on 64 bit CPU's :(

declare int %time(int*) ;void* actually
declare int %clock()
declare void %sleep(int)

; End of external declarations
"""

extfunctions = """; External functions (will be inlined by LLVM)

double %ll_time_time() {
    %v0 = call int %time(int* null)
    %v1 = cast int %v0 to double
    ret double %v1
}

double %ll_time_clock() {
    %v0 = call int %clock()
    %v1 = cast int %v0 to double
    %v2 = div double %v1, 1000000.0    ;CLOCKS_PER_SEC
    ret double %v2
}

void %ll_time_sleep__Float(double %f) {
    %i = cast double %f to int
    call void %sleep(int %i)
    ret void
}

; End of external functions
"""
