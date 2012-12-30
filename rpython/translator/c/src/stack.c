/* Stack operation */
#include <src/stack.h>
#include <src/thread.h>
#include <stdio.h>


/* the current stack is in the interval [end-length:end].  We assume a
   stack that grows downward here. */
char *_LLstacktoobig_stack_end = NULL;
long _LLstacktoobig_stack_length = MAX_STACK_SIZE;
char _LLstacktoobig_report_error = 1;
static RPyThreadStaticTLS end_tls_key;

void LL_stack_set_length_fraction(double fraction)
{
	_LLstacktoobig_stack_length = (long)(MAX_STACK_SIZE * fraction);
}

char LL_stack_too_big_slowpath(long current)
{
	long diff, max_stack_size;
	char *baseptr, *curptr = (char*)current;

	/* The stack_end variable is updated to match the current value
	   if it is still 0 or if we later find a 'curptr' position
	   that is above it.  The real stack_end pointer is stored in
	   thread-local storage, but we try to minimize its overhead by
	   keeping a local copy in _LLstacktoobig_stack_end. */

	if (_LLstacktoobig_stack_end == NULL) {
		/* not initialized */
		/* XXX We assume that initialization is performed early,
		   when there is still only one thread running.  This
		   allows us to ignore race conditions here */
		char *errmsg = RPyThreadStaticTLS_Create(&end_tls_key);
		if (errmsg) {
			/* XXX should we exit the process? */
			fprintf(stderr, "Internal PyPy error: %s\n", errmsg);
			return 1;
		}
	}

	baseptr = (char *) RPyThreadStaticTLS_Get(end_tls_key);
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
	RPyThreadStaticTLS_Set(end_tls_key, baseptr);
	_LLstacktoobig_stack_end = baseptr;
	return 0;
}
