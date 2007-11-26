
/************************************************************/
 /***  C header subsection: stack operations               ***/

#include <unistd.h>

#ifndef MAX_STACK_SIZE
#    define MAX_STACK_SIZE (1 << 19)
#endif

void LL_stack_unwind(void);
int LL_stack_too_big(void);

#ifndef PYPY_NOT_MAIN_FILE
#include <stdio.h>
#include "thread.h"

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

int LL_stack_too_big(void)
{
	char local;
	long diff;
	char *baseptr;
	static volatile char *stack_base_pointer = NULL;
	static long stack_min = 0;
	static long stack_max = 0;
	static RPyThreadStaticTLS stack_base_pointer_key;
	/* Check that the stack is less than MAX_STACK_SIZE bytes bigger
	   than the value recorded in stack_base_pointer.  The base
	   pointer is updated to the current value if it is still NULL
	   or if we later find a &local that is below it.  The real
	   stack base pointer is stored in thread-local storage, but we
	   try to minimize its overhead by keeping a local copy in
	   stack_pointer_pointer. */

	diff = &local - stack_base_pointer;
	if (stack_min <= diff && diff <= stack_max) {
		/* common case: we are still in the same thread as last time
		   we checked, and still in the allowed part of the stack */
		return 0;
	}

	if (stack_min == stack_max /* == 0 */) {
		/* not initialized */
		/* XXX We assume that initialization is performed early,
		   when there is still only one thread running.  This
		   allows us to ignore race conditions here */
		char *errmsg = RPyThreadStaticTLS_Create(&stack_base_pointer_key);
		if (errmsg) {
			/* XXX should we exit the process? */
			fprintf(stderr, "Internal PyPy error: %s\n", errmsg);
			return 1;
		}
		if (_LL_stack_growing_direction(NULL) > 0)
			stack_max = MAX_STACK_SIZE;
		else
			stack_min = -MAX_STACK_SIZE;
	}

	baseptr = (char *) RPyThreadStaticTLS_Get(stack_base_pointer_key);
	if (baseptr != NULL) {
		diff = &local - baseptr;
		if (stack_min <= diff && diff <= stack_max) {
			/* within bounds */
			stack_base_pointer = baseptr;
			return 0;
		}

		if ((stack_min == 0 && diff < 0) ||
		    (stack_max == 0 && diff > 0)) {
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
	RPyThreadStaticTLS_Set(stack_base_pointer_key, baseptr);
	stack_base_pointer = baseptr;
	return 0;
}

#endif
