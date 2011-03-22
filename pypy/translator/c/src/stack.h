
/************************************************************/
 /***  C header subsection: stack operations               ***/

#ifndef MAX_STACK_SIZE
#    define MAX_STACK_SIZE (3 << 18)    /* 768 kb */
#endif

/* This include must be done in any case to initialise
 * the header dependencies early (winsock2, before windows.h).
 * It is needed to have RPyThreadStaticTLS, too. */
#include "thread.h"

extern char *_LLstacktoobig_stack_start;

void LL_stack_unwind(void);
char LL_stack_too_big_slowpath(long);    /* returns 0 (ok) or 1 (too big) */

/* some macros referenced from pypy.rlib.rstack */
#define LL_stack_get_start() ((long)_LLstacktoobig_stack_start)
#define LL_stack_get_length() MAX_STACK_SIZE
#define LL_stack_get_start_adr() ((long)&_LLstacktoobig_stack_start)  /* JIT */


#ifdef __GNUC__
#  define PYPY_INHIBIT_TAIL_CALL()   asm("/* inhibit_tail_call */")
#else
#  define PYPY_INHIBIT_TAIL_CALL()   /* add hints for other compilers here */
#endif


#ifndef PYPY_NOT_MAIN_FILE
#include <stdio.h>

#ifndef PYPY_NOINLINE
# if defined __GNUC__
#  define PYPY_NOINLINE __attribute__((noinline))
# else
// add hints for other compilers here ...
#  define PYPY_NOINLINE
# endif
#endif

long PYPY_NOINLINE _LL_stack_growing_direction(char *parent)
{
	char local;
	if (parent == NULL)
		return _LL_stack_growing_direction(&local);
	else
		return &local - parent;
}

char *_LLstacktoobig_stack_start = NULL;
int stack_direction = 0;
RPyThreadStaticTLS start_tls_key;

char LL_stack_too_big_slowpath(long current)
{
	long diff;
	char *baseptr, *curptr = (char*)current;

	/* The stack_start variable is updated to match the current value
	   if it is still 0 or if we later find a 'curptr' position
	   that is below it.  The real stack_start pointer is stored in
	   thread-local storage, but we try to minimize its overhead by
	   keeping a local copy in _LLstacktoobig_stack_start. */

	if (stack_direction == 0) {
		/* not initialized */
		/* XXX We assume that initialization is performed early,
		   when there is still only one thread running.  This
		   allows us to ignore race conditions here */
		char *errmsg = RPyThreadStaticTLS_Create(&start_tls_key);
		if (errmsg) {
			/* XXX should we exit the process? */
			fprintf(stderr, "Internal PyPy error: %s\n", errmsg);
			return 1;
		}
		if (_LL_stack_growing_direction(NULL) > 0)
			stack_direction = +1;
		else
			stack_direction = -1;
	}

	baseptr = (char *) RPyThreadStaticTLS_Get(start_tls_key);
	if (baseptr != NULL) {
		diff = curptr - baseptr;
		if (((unsigned long)diff) < (unsigned long)MAX_STACK_SIZE) {
			/* within bounds, probably just had a thread switch */
			_LLstacktoobig_stack_start = baseptr;
			return 0;
		}

		if (stack_direction > 0) {
			if (diff < 0 && diff > -MAX_STACK_SIZE)
				;           /* stack underflow */
			else
				return 1;   /* stack overflow (probably) */
		}
		else {
			if (diff >= MAX_STACK_SIZE && diff < 2*MAX_STACK_SIZE)
				;           /* stack underflow */
			else
				return 1;   /* stack overflow (probably) */
		}
		/* else we underflowed the stack, which means that
		   the initial estimation of the stack base must
		   be revised */
	}

	/* update the stack base pointer to the current value */
	if (stack_direction > 0) {
		/* the valid range is [curptr:curptr+MAX_STACK_SIZE] */
		baseptr = curptr;
	}
	else {
		/* the valid range is [curptr-MAX_STACK_SIZE+1:curptr+1] */
		baseptr = curptr - MAX_STACK_SIZE + 1;
	}
	RPyThreadStaticTLS_Set(start_tls_key, baseptr);
	_LLstacktoobig_stack_start = baseptr;
	return 0;
}

#endif
