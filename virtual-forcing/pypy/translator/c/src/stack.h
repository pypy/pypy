
/************************************************************/
 /***  C header subsection: stack operations               ***/

#ifndef MAX_STACK_SIZE
#    define MAX_STACK_SIZE (1 << 19)
#endif

/* This include must be done in any case to initialise
 * the header dependencies early (thread -> winsock2, before windows.h) */
#include "thread.h"

void LL_stack_unwind(void);
int LL_stack_too_big_slowpath(void);

extern volatile char *_LLstacktoobig_stack_base_pointer;
extern long _LLstacktoobig_stack_min;
extern long _LLstacktoobig_stack_max;

static int LL_stack_too_big(void)
{
	/* The fast path of stack_too_big, called extremely often.
	   Making it static makes an *inlinable* copy of this small
	   function's implementation in each compilation unit. */
	char local;
	long diff = &local - _LLstacktoobig_stack_base_pointer;
	/* common case: we are still in the same thread as last time
	   we checked, and still in the allowed part of the stack */
	return ((diff < _LLstacktoobig_stack_min ||
		 diff > _LLstacktoobig_stack_max)
		/* if not, call the slow path */
		&& LL_stack_too_big_slowpath());
}


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

volatile char *_LLstacktoobig_stack_base_pointer = NULL;
long _LLstacktoobig_stack_min = 0;
long _LLstacktoobig_stack_max = 0;
RPyThreadStaticTLS _LLstacktoobig_stack_base_pointer_key;

int LL_stack_too_big_slowpath(void)
{
	char local;
	long diff;
	char *baseptr;
	/* Check that the stack is less than MAX_STACK_SIZE bytes bigger
	   than the value recorded in stack_base_pointer.  The base
	   pointer is updated to the current value if it is still NULL
	   or if we later find a &local that is below it.  The real
	   stack base pointer is stored in thread-local storage, but we
	   try to minimize its overhead by keeping a local copy in
	   stack_pointer_pointer. */

	if (_LLstacktoobig_stack_min == _LLstacktoobig_stack_max /* == 0 */) {
		/* not initialized */
		/* XXX We assume that initialization is performed early,
		   when there is still only one thread running.  This
		   allows us to ignore race conditions here */
		char *errmsg = RPyThreadStaticTLS_Create(
			&_LLstacktoobig_stack_base_pointer_key);
		if (errmsg) {
			/* XXX should we exit the process? */
			fprintf(stderr, "Internal PyPy error: %s\n", errmsg);
			return 1;
		}
		if (_LL_stack_growing_direction(NULL) > 0)
			_LLstacktoobig_stack_max = MAX_STACK_SIZE;
		else
			_LLstacktoobig_stack_min = -MAX_STACK_SIZE;
	}

	baseptr = (char *) RPyThreadStaticTLS_Get(
			_LLstacktoobig_stack_base_pointer_key);
	if (baseptr != NULL) {
		diff = &local - baseptr;
		if (_LLstacktoobig_stack_min <= diff &&
		    diff <= _LLstacktoobig_stack_max) {
			/* within bounds */
			_LLstacktoobig_stack_base_pointer = baseptr;
			return 0;
		}

		if ((_LLstacktoobig_stack_min == 0 && diff < 0) ||
		    (_LLstacktoobig_stack_max == 0 && diff > 0)) {
			/* we underflowed the stack, which means that
			   the initial estimation of the stack base must
			   be revised (see below) */
		}
		else {
			return 1;   /* stack overflow */
		}
	}

	/* update the stack base pointer to the current value */
	baseptr = &local;
	RPyThreadStaticTLS_Set(_LLstacktoobig_stack_base_pointer_key, baseptr);
	_LLstacktoobig_stack_base_pointer = baseptr;
	return 0;
}

#endif
