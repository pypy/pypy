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
    %st = alloca int, uint 32
    %error = call ccc int %fstat(int %fd, int* %st)
    ;TODO XXX if error: raise exception
    ;%ret = %ll_stat_result__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed__Signed(
    %ret = alloca %structtype.tuple10   ;ERROR
    store int %s
    ret %structtype.tuple10* %ret
}

""")

#struct stat {
#     0 : dev_t         res2 : st_dev;      /* device */
#     1 : ino_t         res1 : st_ino;      /* inode */
#     2 : mode_t        res0 : st_mode;     /* protection */
#     3 : nlink_t       res3 : st_nlink;    /* number of hard links */
#     4 : uid_t         res4 : st_uid;      /* user ID of owner */
#     5 : gid_t         res5 : st_gid;      /* group ID of owner */
#     6 : dev_t              : st_rdev;     /* device type (if inode device) */
#     7 : off_t         res6 : st_size;     /* total size, in bytes */
#     8 : blksize_t          : st_blksize;  /* blocksize for filesystem I/O */
#     9 : blkcnt_t           : st_blocks;   /* number of blocks allocated */
#    10 : time_t        res7 : st_atime;    /* time of last access */
#    11 : time_t        res8 : st_mtime;    /* time of last modification */
#    12 : time_t        res9 : st_ctime;    /* time of last status change */
#};
