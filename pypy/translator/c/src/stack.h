
/************************************************************/
 /***  C header subsection: stack operations               ***/

extern char *_LLstacktoobig_stack_end;
extern long _LLstacktoobig_stack_length;
extern char _LLstacktoobig_report_error;

char LL_stack_too_big_slowpath(long);    /* returns 0 (ok) or 1 (too big) */
void LL_stack_set_length_fraction(double);

/* some functions referenced from pypy.rlib.rstack */
long LL_stack_get_end();
long LL_stack_get_length();
long LL_stack_get_end_adr();
long LL_stack_get_length_adr();

void LL_stack_criticalcode_start();
void LL_stack_criticalcode_stop();


#ifdef __GNUC__
#  define PYPY_INHIBIT_TAIL_CALL()   asm("/* inhibit_tail_call */")
#else
#  define PYPY_INHIBIT_TAIL_CALL()   /* add hints for other compilers here */
#endif
