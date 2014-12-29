/* Stack operation */
#include "common_header.h"
#include "structdef.h"       /* for struct pypy_threadlocal_s */
#include <src/stack.h>
#include <src/threadlocal.h>
#include <stdio.h>


/* the current stack is in the interval [end-length:end].  We assume a
   stack that grows downward here. */
char *_LLstacktoobig_stack_end = NULL;
long _LLstacktoobig_stack_length = MAX_STACK_SIZE;
char _LLstacktoobig_report_error = 1;

void LL_stack_set_length_fraction(double fraction)
{
	_LLstacktoobig_stack_length = (long)(MAX_STACK_SIZE * fraction);
}

char LL_stack_too_big_slowpath(long current)
{
	long diff, max_stack_size;
	char *baseptr, *curptr = (char*)current;
	char *tl;
	struct pypy_threadlocal_s *tl1;

	/* The stack_end variable is updated to match the current value
	   if it is still 0 or if we later find a 'curptr' position
	   that is above it.  The real stack_end pointer is stored in
	   thread-local storage, but we try to minimize its overhead by
	   keeping a local copy in _LLstacktoobig_stack_end. */

	OP_THREADLOCALREF_ADDR(tl);
	tl1 = (struct pypy_threadlocal_s *)tl;
	baseptr = tl1->stack_end;
	max_stack_size = _LLstacktoobig_stack_length;
	if (baseptr == NULL) {
		/* first time we see this thread */
	}
	else {
		diff = baseptr - curptr;
		if (((unsigned long)diff) <= (unsigned long)max_stack_size) {
			/* within bounds, probably just had a thread switch */
			_LLstacktoobig_stack_end = baseptr;
			return 0;
		}
		if (((unsigned long)-diff) <= (unsigned long)max_stack_size) {
			/* stack underflowed: the initial estimation of
			   the stack base must be revised */
		}
		else {	/* stack overflow (probably) */
			return _LLstacktoobig_report_error;
		}
	}

	/* update the stack base pointer to the current value */
	baseptr = curptr;
	tl1->stack_end = baseptr;
	_LLstacktoobig_stack_end = baseptr;
	return 0;
}
