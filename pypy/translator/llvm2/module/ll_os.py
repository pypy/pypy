extdeclarations = """
;ll_os.py
declare ccc int %dup(int)
declare ccc void %close(int)
declare ccc int %open(sbyte*, int, int)
declare ccc int %write(int, sbyte*, int)
declare ccc int %read(int, sbyte*, int)
declare ccc sbyte* %strncpy(sbyte*, sbyte*, int)
declare ccc int %strlen(sbyte*)
declare ccc int %isatty(int)
declare ccc int %stat(sbyte*, [32 x int]*)
declare ccc int %fstat(int, [32 x int]*)
declare ccc int %lseek(int, int, int)
declare ccc int %ftruncate(int, int)
declare ccc sbyte* %getcwd(sbyte*, int)

%errno = external global int

%__ll_os_getcwd             = internal constant [12 x sbyte] c"getcwd.....\\00"
%__ll_os_ftruncate          = internal constant [12 x sbyte] c"ftruncate..\\00"
%__ll_os_lseek              = internal constant [12 x sbyte] c"lseek......\\00"
%__ll_os_stat               = internal constant [12 x sbyte] c"stat.......\\00"
%__ll_os_fstat              = internal constant [12 x sbyte] c"fstat......\\00"
"""

extfunctions = {}

extfunctions["%ll_os_dup"] = ((), """
internal fastcc int %ll_os_dup(int %fd) {
    %ret = call ccc int %dup(int %fd)
    ret int %ret
}

""")

extfunctions["%ll_os_getcwd"] = (("%string_to_RPyString", "%__debug"), """
internal fastcc %RPyString* %ll_os_getcwd() {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_getcwd) ; XXX: Test: ll_os_getcwd

    %s = alloca sbyte, uint 1024
    %res = call ccc sbyte* %getcwd(sbyte* %s, int 1023)
    ;if %res == null: raise...

    %cwd = call fastcc %RPyString* %string_to_RPyString(sbyte* %s)
    ret %RPyString* %cwd
}

""")

extfunctions["%ll_os_close"] = ((), """
internal fastcc void %ll_os_close(int %fd) {
    call ccc void %close(int %fd)
    ret void
}

""")

extfunctions["%ll_os_open"] = (("%cast",), """
internal fastcc int %ll_os_open(%RPyString* %structstring, int %flag, int %mode) {
    %dest  = call fastcc sbyte* %cast(%RPyString* %structstring)
    %fd    = call ccc    int    %open(sbyte* %dest, int %flag, int %mode)
    ret int %fd 
}

""")

extfunctions["%ll_os_write"] = (("%cast",), """
internal fastcc int %ll_os_write(int %fd, %RPyString* %structstring) {
    %reallengthptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 
    %dest          = call fastcc sbyte* %cast(%RPyString* %structstring)
    %byteswritten  = call ccc    int    %write(int %fd, sbyte* %dest, int %reallength)
    ret int %byteswritten
}

""")

extfunctions["%ll_read_into"] = ((), """
internal fastcc int %ll_read_into(int %fd, %RPyString* %structstring) {
    %reallengthptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %reallength    = load int* %reallengthptr 

    %destptr   = getelementptr %RPyString* %structstring, int 0, uint 1, uint 1
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

extfunctions["%ll_os_ftruncate"] = (("%__debug",), """
internal fastcc void %ll_os_ftruncate(int %fd, int %length) {
    call fastcc void %__debug([12 x sbyte]* %__ll_os_ftruncate) ; XXX: Test: ll_os_ftruncate
    %res = call ccc int %ftruncate(int %fd, int %length)
    ;if res < 0 raise...
    ret void
}
""")

extfunctions["%ll_os_lseek"] = (("%__debug",), """
internal fastcc int %ll_os_lseek(int %fd, int %pos, int %how) {
    call fastcc void %__debug([12 x sbyte]* %__ll_os_lseek) ; XXX: Test: ll_os_lseek
    ;TODO: determine correct %how
    %res = call ccc int %lseek(int %fd, int %pos, int %how)
    ;if res < 0 raise...
    ret int %res
}
""")

extfunctions["%_stat_construct_result_helper"] = ((), """
internal fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x int]* %src) {

    %src0ptr = getelementptr [32 x int]* %src, int 0, uint 4    ;st_mode
    %src1ptr = getelementptr [32 x int]* %src, int 0, uint 3    ;st_ino
    %src2ptr = getelementptr [32 x int]* %src, int 0, uint 0    ;st_dev
    %src3ptr = getelementptr [32 x int]* %src, int 0, uint 5    ;st_nlink
    %src4ptr = getelementptr [32 x int]* %src, int 0, uint 6    ;st_uid
    %src5ptr = getelementptr [32 x int]* %src, int 0, uint 7    ;st_gid
    %src6ptr = getelementptr [32 x int]* %src, int 0, uint 11   ;st_size
    %src7ptr = getelementptr [32 x int]* %src, int 0, uint 14   ;st_atime
    %src8ptr = getelementptr [32 x int]* %src, int 0, uint 16   ;st_mtime
    %src9ptr = getelementptr [32 x int]* %src, int 0, uint 18   ;st_ctime

    %src0 = load int* %src0ptr
    %src1 = load int* %src1ptr
    %src2 = load int* %src2ptr
    %src3 = load int* %src3ptr
    %src4 = load int* %src4ptr
    %src5 = load int* %src5ptr
    %src6 = load int* %src6ptr
    %src7 = load int* %src7ptr
    %src8 = load int* %src8ptr
    %src9 = load int* %src9ptr

    %malloc.Size  = getelementptr %RPySTAT_RESULT* null, uint 1
    %malloc.SizeU = cast %RPySTAT_RESULT* %malloc.Size to uint
    %malloc.Ptr   = call fastcc sbyte* %gc_malloc_atomic(uint %malloc.SizeU)
    %dest         = cast sbyte* %malloc.Ptr to %RPySTAT_RESULT*

    %dest0ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 0
    %dest1ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 1
    %dest2ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 2
    %dest3ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 3
    %dest4ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 4
    %dest5ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 5
    %dest6ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 6
    %dest7ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 7
    %dest8ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 8
    %dest9ptr = getelementptr %RPySTAT_RESULT* %dest, int 0, uint 9

    store int %src0, int* %dest0ptr
    store int %src1, int* %dest1ptr
    store int %src2, int* %dest2ptr
    store int %src3, int* %dest3ptr
    store int %src4, int* %dest4ptr
    store int %src5, int* %dest5ptr
    store int %src6, int* %dest6ptr
    store int %src7, int* %dest7ptr
    store int %src8, int* %dest8ptr
    store int %src9, int* %dest9ptr

    ret %RPySTAT_RESULT* %dest
}
""")

extfunctions["%ll_os_stat"] = (("%cast", "%__debug", "%_stat_construct_result_helper"), """
internal fastcc %RPySTAT_RESULT* %ll_os_stat(%RPyString* %s) {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_stat) ; XXX: Test: ll_os_stat

    %st       = alloca [32 x int]
    %filename = call fastcc sbyte* %cast(%RPyString* %s)
    %error    = call ccc int %stat(sbyte* %filename, [32 x int]* %st)
    %cond     = seteq int %error, 0
    br bool %cond, label %cool, label %bwa

bwa:
    %errno_ = load int* %errno
    call fastcc void %ll_raise_OSError__Signed(int %errno_)
    ret %RPySTAT_RESULT* null

cool:
    %result = call fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x int]* %st)
    ret %RPySTAT_RESULT* %result
}
""")

extfunctions["%ll_os_fstat"] = (("%__debug", "%_stat_construct_result_helper"), """
internal fastcc %RPySTAT_RESULT* %ll_os_fstat(int %fd) {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_fstat) ; XXX: Test: ll_os_fstat

    %st    = alloca [32 x int]
    %error = call ccc int %fstat(int %fd, [32 x int]* %st)
    %cond  = seteq int %error, 0
    br bool %cond, label %cool, label %bwa

bwa:
    %errno_ = load int* %errno
    call fastcc void %ll_raise_OSError__Signed(int %errno_)
    ret %RPySTAT_RESULT* null

cool:
    %result = call fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x int]* %st)
    ret %RPySTAT_RESULT* %result
}

""")
