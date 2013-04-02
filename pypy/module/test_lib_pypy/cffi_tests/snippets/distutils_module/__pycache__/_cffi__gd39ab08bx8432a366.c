
#include <stdio.h>
#include <stddef.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/types.h>   /* XXX for ssize_t on some platforms */

#ifdef _WIN32
#  include <Windows.h>
#  define snprintf _snprintf
typedef __int8 int8_t;
typedef __int16 int16_t;
typedef __int32 int32_t;
typedef __int64 int64_t;
typedef unsigned __int8 uint8_t;
typedef unsigned __int16 uint16_t;
typedef unsigned __int32 uint32_t;
typedef unsigned __int64 uint64_t;
typedef SSIZE_T ssize_t;
typedef unsigned char _Bool;
#else
#  include <stdint.h>
#endif

   // passed to the real C compiler
#include <sys/types.h>
#include <pwd.h>

struct passwd * _cffi_f_getpwuid(int x0)
{
  return getpwuid(x0);
}

static void _cffi_check_struct_passwd(struct passwd *p)
{
  /* only to generate compile-time warnings or errors */
  { char * *tmp = &p->pw_name; (void)tmp; }
}
ssize_t _cffi_layout_struct_passwd(ssize_t i)
{
  struct _cffi_aligncheck { char x; struct passwd y; };
  static ssize_t nums[] = {
    sizeof(struct passwd),
    offsetof(struct _cffi_aligncheck, y),
    offsetof(struct passwd, pw_name),
    sizeof(((struct passwd *)0)->pw_name),
    -1
  };
  return nums[i];
  /* the next line is not executed, but compiled */
  _cffi_check_struct_passwd(0);
}

