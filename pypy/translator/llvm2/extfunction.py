extdeclarations =  """
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

"""

gc_boehm = """
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

gc_disabled = """
sbyte* %gc_malloc(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

"""

extfunctions = {}   #dependencies, llvm-code

extfunctions["%cast"] = ((), """
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

""")

extfunctions["%new.st.var.rpy_string.0.helper"] = ((), """
%st.rpy_string.0 * %new.st.var.rpy_string.0.helper(int %len) {
    %size = getelementptr %st.rpy_string.0* null, int 0, uint 1, uint 1, int %len
    %usize = cast sbyte* %size to uint
    %malloc.Size.5 = getelementptr sbyte* null, uint %usize
    %malloc.SizeU.5 = cast sbyte* %malloc.Size.5 to uint
    %malloc.Ptr.5 = call sbyte* %gc_malloc(uint %malloc.SizeU.5)
    %ptr = cast sbyte* %malloc.Ptr.5 to sbyte*
    %result = cast sbyte* %ptr to %st.rpy_string.0*
    %arraylength = getelementptr %st.rpy_string.0* %result, int 0, uint 1, uint 0
    store int %len, int* %arraylength
    ret %st.rpy_string.0* %result
}

""")

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
    ; XXX how to get at the proper division constant per platform? 
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

extfunctions["%ll_os_open"] = (("%cast",), """
int %ll_os_open(%st.rpy_string.0* %structstring, int %flag, int %mode) {
    %dest  = call sbyte* %cast(%st.rpy_string.0* %structstring)
    %fd    = call int    %open(sbyte* %dest, int %flag, int %mode)
    ret int %fd 
}

""")

extfunctions["%ll_os_write"] = (("%cast",), """
int %ll_os_write(int %fd, %st.rpy_string.0* %structstring) {
    %reallengthptr = getelementptr %st.rpy_string.0* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 
    %dest          = call sbyte* %cast(%st.rpy_string.0* %structstring)
    %byteswritten  = call int    %write(int %fd, sbyte* %dest, int %reallength)
    ret int %byteswritten
}

""")

extfunctions["%ll_os_read"] = (("%new.st.var.rpy_string.0.helper",), """
%st.rpy_string.0* %ll_os_read(int %fd, int %buffersize) {
    ;This is a bit simplistic! It really allocated a large enough buffer to hold all the data in.
    %str = call %st.rpy_string.0* %new.st.var.rpy_string.0.helper(int %buffersize)

    ;load the actual data
    %destptr   = getelementptr %st.rpy_string.0* %str, int 0, uint 1, uint 1
    %dest      = cast [0 x sbyte]* %destptr to sbyte*
    %bytesread = call int %read(int %fd, sbyte* %dest, int %buffersize)
    
    ;set str.length to number of bytes read
    %reallengthptr = getelementptr %st.rpy_string.0* %str, int 0, uint 1, uint 0
    store int %bytesread, int* %reallengthptr

    ret %st.rpy_string.0* %str
}

""")

def dependencies(funcname, deplist):
    deplist.append(funcname)
    if funcname in extfunctions:
        for depfuncname in extfunctions[funcname][0]:
            if depfuncname not in deplist:  #avoid loops
                dependencies(depfuncname, deplist)
    return deplist
