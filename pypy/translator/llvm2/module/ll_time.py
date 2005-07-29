extdeclarations = '''
;ll_time.py
declare int %time(int*) ;void* actually
declare int %clock()
declare void %sleep(int)
'''

extfunctions = {}

extfunctions["%ll_time_time"] = ((), """
double %ll_time_time() {
    %v0 = call int %time(int* null)
    %v1 = cast int %v0 to double
    ret double %v1
}

""")

extfunctions["%ll_time_clock"] = ((), """
double %ll_time_clock() {
    %v0 = call int %clock()
    %v1 = cast int %v0 to double
    ; XXX how to get at the proper division (or any other) constant per platform?
    %v2 = div double %v1, 1000000.0    ;CLOCKS_PER_SEC accrdoing to single unix spec
    ret double %v2
}

""")

extfunctions["%ll_time_sleep"] = ((), """
void %ll_time_sleep(double %f) {
    %i = cast double %f to int
    call void %sleep(int %i)
    ret void
}

""")
