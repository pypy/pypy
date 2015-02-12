
/************************************************************/
 /***  C header subsection: stack operations               ***/

#include <src/precommondefs.h>


#ifndef MAX_STACK_SIZE
#    define MAX_STACK_SIZE (3 << 18)    /* 768 kb */
#endif


RPY_EXTERN char *_LLstacktoobig_stack_end;
RPY_EXTERN long _LLstacktoobig_stack_length;
RPY_EXTERN char _LLstacktoobig_report_error;

RPY_EXTERN
char LL_stack_too_big_slowpath(long);    /* returns 0 (ok) or 1 (too big) */
RPY_EXTERN
void LL_stack_set_length_fraction(double);

/* some macros referenced from rpython.rlib.rstack */
#define LL_stack_get_end() ((long)_LLstacktoobig_stack_end)
#define LL_stack_get_length() _LLstacktoobig_stack_length
#define LL_stack_get_end_adr()    ((long)&_LLstacktoobig_stack_end)   /* JIT */
#define LL_stack_get_length_adr() ((long)&_LLstacktoobig_stack_length)/* JIT */

#define LL_stack_criticalcode_start()  (_LLstacktoobig_report_error = 0)
#define LL_stack_criticalcode_stop()   (_LLstacktoobig_report_error = 1)


#ifdef __GNUC__
#  define PYPY_INHIBIT_TAIL_CALL()   asm("/* inhibit_tail_call */")
#else
#  define PYPY_INHIBIT_TAIL_CALL()   /* add hints for other compilers here */
#endif


