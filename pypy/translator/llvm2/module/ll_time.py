extdeclarations = '''
;ll_time.py
declare ccc int %time(int*) ;void* actually
declare ccc int %clock()
declare ccc void %sleep(int)
'''

extfunctions = {}

extfunctions["%ll_time_time"] = ((), """
fastcc double %ll_time_time() {
    %v0 = call ccc int %time(int* null)
    %v1 = cast int %v0 to double
    ret double %v1
}

""")

extfunctions["%ll_time_clock"] = ((), """
fastcc double %ll_time_clock() {
    %v0 = call ccc int %clock()
    %v1 = cast int %v0 to double
    ; XXX how to get at the proper division (or any other) constant per platform?
    %v2 = div double %v1, 1000000.0    ;CLOCKS_PER_SEC accrdoing to single unix spec
    ret double %v2
}

""")

extfunctions["%ll_time_sleep"] = ((), """
fastcc void %ll_time_sleep(double %f) {
    %i = cast double %f to int
    call ccc void %sleep(int %i)
    ret void
}

""")
