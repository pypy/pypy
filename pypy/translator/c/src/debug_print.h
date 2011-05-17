/************************************************************/
 /***  C header subsection: debug_print & related tools    ***/

/* values of the PYPYLOG environment variable:
   ("top-level" debug_prints means not between debug_start and debug_stop)

   (empty)        logging is turned off, apart from top-level debug_prints
                     that go to stderr
   fname          logging for profiling: includes all debug_start/debug_stop
                     but not any nested debug_print
   :fname         full logging
   prefix:fname   conditional logging
   prefix1,prefix2:fname   conditional logging with multiple selections

   Conditional logging means that it only includes the debug_start/debug_stop
   sections whose name match 'prefix'.  Other sections are ignored, including
   all debug_prints that occur while this section is running and all nested
   subsections.

   Note that 'fname' can be '-' to send the logging data to stderr.
*/

/* macros used by the generated code */
#define PYPY_HAVE_DEBUG_PRINTS    (pypy_have_debug_prints & 1 ? \
                                   (pypy_debug_ensure_opened(), 1) : 0)
#define PYPY_DEBUG_FILE           pypy_debug_file
#define PYPY_DEBUG_START(cat)     pypy_debug_start(cat)
#define PYPY_DEBUG_STOP(cat)      pypy_debug_stop(cat)
#define OP_DEBUG_OFFSET(res)      res = pypy_debug_offset()
#define OP_HAVE_DEBUG_PRINTS(r)   r = (pypy_have_debug_prints & 1)
#define OP_DEBUG_FLUSH() fflush(pypy_debug_file)

/************************************************************/

/* prototypes (internal use only) */
void pypy_debug_ensure_opened(void);
void pypy_debug_start(const char *category);
void pypy_debug_stop(const char *category);
long pypy_debug_offset(void);

extern long pypy_have_debug_prints;
extern FILE *pypy_debug_file;

#define OP_LL_READ_TIMESTAMP(val) READ_TIMESTAMP(val)

#include "src/asm.h"

/* asm_xxx.h may contain a specific implementation of READ_TIMESTAMP.
 * This is the default generic timestamp implementation.
 */
#ifndef READ_TIMESTAMP

#  ifdef _WIN32
#    define READ_TIMESTAMP(val) QueryPerformanceCounter((LARGE_INTEGER*)&(val))
#  else
#    include <time.h>
#    include <sys/time.h>

long long pypy_read_timestamp();

#    define READ_TIMESTAMP(val)  (val) = pypy_read_timestamp()

#  endif
#endif
