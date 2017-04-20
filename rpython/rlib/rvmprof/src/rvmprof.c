#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */

#else
#  include "common_header.h"
#  include "structdef.h"
#  include "src/threadlocal.h"
#  include "rvmprof.h"
#  include "forwarddecl.h"
#endif



#include "shared/vmprof_get_custom_offset.h"
#ifdef VMPROF_UNIX
#include "shared/vmprof_main.h"
#else
#include "shared/vmprof_main_win32.h"
#endif


#ifdef RPYTHON_LL2CTYPES
int IS_VMPROF_EVAL(void * ptr) { return 0; }
#else
int IS_VMPROF_EVAL(void * ptr)
{
    return ptr == __vmprof_eval_vmprof;
}
#endif


long vmprof_get_profile_path(const char * buffer, long size)
{
    return vmp_fd_to_path(vmp_profile_fileno(), buffer, size);
}
