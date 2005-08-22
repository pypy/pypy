extdeclarations = """
;ll_os.py
declare ccc INT %dup(INT)
declare ccc void %close(INT)
declare ccc INT %open(sbyte*, INT, INT)
declare ccc INT %write(INT, sbyte*, INT)
declare ccc INT %read(INT, sbyte*, INT)
declare ccc sbyte* %strncpy(sbyte*, sbyte*, INT)
declare ccc INT %isatty(INT)
declare ccc INT %stat(sbyte*, [32 x INT]*)
declare ccc INT %fstat(INT, [32 x INT]*)
declare ccc INT %lseek(INT, INT, INT)
declare ccc INT %ftruncate(INT, INT)
declare ccc sbyte* %getcwd(sbyte*, INT)

%errno = external global INT

%__ll_os_getcwd             = internal constant [12 x sbyte] c"getcwd.....\\00"
%__ll_os_ftruncate          = internal constant [12 x sbyte] c"ftruncate..\\00"
%__ll_os_lseek              = internal constant [12 x sbyte] c"lseek......\\00"
%__ll_os_stat               = internal constant [12 x sbyte] c"stat.......\\00"
%__ll_os_fstat              = internal constant [12 x sbyte] c"fstat......\\00"
"""

extfunctions = {}

extfunctions["%ll_os_dup"] = ((), """
internal fastcc INT %ll_os_dup(INT %fd) {
    %ret = call ccc INT %dup(INT %fd)
    ret INT %ret
}

""")

extfunctions["%ll_os_getcwd"] = (("%string_to_RPyString", "%__debug"), """
internal fastcc %RPyString* %ll_os_getcwd() {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_getcwd) ; XXX: Test: ll_os_getcwd

    %s = alloca sbyte, UINT 1024
    %res = call ccc sbyte* %getcwd(sbyte* %s, INT 1023)
    ;if %res == null: raise...

    %cwd = call fastcc %RPyString* %string_to_RPyString(sbyte* %s)
    ret %RPyString* %cwd
}

""")

extfunctions["%ll_os_close"] = ((), """
internal fastcc void %ll_os_close(INT %fd) {
    call ccc void %close(INT %fd)
    ret void
}

""")

extfunctions["%ll_os_open"] = (("%cast",), """
internal fastcc INT %ll_os_open(%RPyString* %structstring, INT %flag, INT %mode) {
    %dest  = call fastcc sbyte* %cast(%RPyString* %structstring)
    %fd    = call ccc    INT    %open(sbyte* %dest, INT %flag, INT %mode)
    ret INT %fd 
}

""")

extfunctions["%ll_os_write"] = (("%cast",), """
internal fastcc INT %ll_os_write(INT %fd, %RPyString* %structstring) {
    %reallengthptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %reallength    = load INT* %reallengthptr 
    %dest          = call fastcc sbyte* %cast(%RPyString* %structstring)
    %byteswritten  = call ccc    INT    %write(INT %fd, sbyte* %dest, INT %reallength)
    ret INT %byteswritten
}

""")

extfunctions["%ll_read_into"] = ((), """
internal fastcc INT %ll_read_into(INT %fd, %RPyString* %structstring) {
    %reallengthptr = getelementptr %RPyString* %structstring, int 0, uint 1, uint 0
    %reallength    = load INT* %reallengthptr 

    %destptr   = getelementptr %RPyString* %structstring, int 0, uint 1, uint 1
    %dest      = cast [0 x sbyte]* %destptr to sbyte*

    %bytesread = call ccc INT %read(INT %fd, sbyte* %dest, INT %reallength)
    ret INT %bytesread
}

""")

extfunctions["%ll_os_isatty"] = ((), """
internal fastcc bool %ll_os_isatty(INT %fd) {
    %ret = call ccc INT %isatty(INT %fd)
    %ret.bool = cast INT %ret to bool
    ret bool %ret.bool
}

""")

extfunctions["%ll_os_ftruncate"] = (("%__debug",), """
internal fastcc void %ll_os_ftruncate(INT %fd, INT %length) {
    call fastcc void %__debug([12 x sbyte]* %__ll_os_ftruncate) ; XXX: Test: ll_os_ftruncate
    %res = call ccc INT %ftruncate(INT %fd, INT %length)
    ;if res < 0 raise...
    ret void
}
""")

extfunctions["%ll_os_lseek"] = (("%__debug",), """
internal fastcc INT %ll_os_lseek(INT %fd, INT %pos, INT %how) {
    call fastcc void %__debug([12 x sbyte]* %__ll_os_lseek) ; XXX: Test: ll_os_lseek
    ;TODO: determine correct %how
    %res = call ccc INT %lseek(INT %fd, INT %pos, INT %how)
    ;if res < 0 raise...
    ret INT %res
}
""")

extfunctions["%_stat_construct_result_helper"] = ((), """
internal fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x INT]* %src) {

    %src0ptr = getelementptr [32 x INT]* %src, int 0, uint 4    ;st_mode
    %src1ptr = getelementptr [32 x INT]* %src, int 0, uint 3    ;st_ino
    %src2ptr = getelementptr [32 x INT]* %src, int 0, uint 0    ;st_dev
    %src3ptr = getelementptr [32 x INT]* %src, int 0, uint 5    ;st_nlink
    %src4ptr = getelementptr [32 x INT]* %src, int 0, uint 6    ;st_uid
    %src5ptr = getelementptr [32 x INT]* %src, int 0, uint 7    ;st_gid
    %src6ptr = getelementptr [32 x INT]* %src, int 0, uint 11   ;st_size
    %src7ptr = getelementptr [32 x INT]* %src, int 0, uint 14   ;st_atime
    %src8ptr = getelementptr [32 x INT]* %src, int 0, uint 16   ;st_mtime
    %src9ptr = getelementptr [32 x INT]* %src, int 0, uint 18   ;st_ctime

    %src0 = load INT* %src0ptr
    %src1 = load INT* %src1ptr
    %src2 = load INT* %src2ptr
    %src3 = load INT* %src3ptr
    %src4 = load INT* %src4ptr
    %src5 = load INT* %src5ptr
    %src6 = load INT* %src6ptr
    %src7 = load INT* %src7ptr
    %src8 = load INT* %src8ptr
    %src9 = load INT* %src9ptr

    %malloc.Size  = getelementptr %RPySTAT_RESULT* null, uint 1
    %malloc.SizeU = cast %RPySTAT_RESULT* %malloc.Size to UINT
    %malloc.Ptr   = call fastcc sbyte* %gc_malloc_atomic(UINT %malloc.SizeU)
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

    store INT %src0, INT* %dest0ptr
    store INT %src1, INT* %dest1ptr
    store INT %src2, INT* %dest2ptr
    store INT %src3, INT* %dest3ptr
    store INT %src4, INT* %dest4ptr
    store INT %src5, INT* %dest5ptr
    store INT %src6, INT* %dest6ptr
    store INT %src7, INT* %dest7ptr
    store INT %src8, INT* %dest8ptr
    store INT %src9, INT* %dest9ptr

    ret %RPySTAT_RESULT* %dest
}
""")

extfunctions["%ll_os_stat"] = (("%cast", "%__debug", "%_stat_construct_result_helper"), """
internal fastcc %RPySTAT_RESULT* %ll_os_stat(%RPyString* %s) {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_stat) ; XXX: Test: ll_os_stat

    %st       = alloca [32 x INT]
    %filename = call fastcc sbyte* %cast(%RPyString* %s)
    %error    = call ccc INT %stat(sbyte* %filename, [32 x INT]* %st)
    %cond     = seteq INT %error, 0
    br bool %cond, label %cool, label %bwa

bwa:
    %errno_ = load INT* %errno
    call fastcc void %ll_raise_OSError__Signed(INT %errno_)
    ret %RPySTAT_RESULT* null

cool:
    %result = call fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x INT]* %st)
    ret %RPySTAT_RESULT* %result
}
""")

extfunctions["%ll_os_fstat"] = (("%__debug", "%_stat_construct_result_helper"), """
internal fastcc %RPySTAT_RESULT* %ll_os_fstat(INT %fd) {

    call fastcc void %__debug([12 x sbyte]* %__ll_os_fstat) ; XXX: Test: ll_os_fstat

    %st    = alloca [32 x INT]
    %error = call ccc INT %fstat(INT %fd, [32 x INT]* %st)
    %cond  = seteq INT %error, 0
    br bool %cond, label %cool, label %bwa

bwa:
    %errno_ = load INT* %errno
    call fastcc void %ll_raise_OSError__Signed(INT %errno_)
    ret %RPySTAT_RESULT* null

cool:
    %result = call fastcc %RPySTAT_RESULT* %_stat_construct_result_helper([32 x INT]* %st)
    ret %RPySTAT_RESULT* %result
}

""")
