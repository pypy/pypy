/* Stack operation */
#include "common_header.h"
#include "structdef.h"       /* for struct pypy_threadlocal_s */
#include <src/stack.h>
#include <src/threadlocal.h>
#include <stdio.h>
#ifndef _WIN32
#  include <sys/resource.h>   /* for getrlimit(RLIMIT_STACK) */
#endif


/* the current stack is in the interval [end-length:end].  We assume a
   stack that grows downward here. */

/* (stored in a struct to ensure that stack_end and stack_length are
   close together; used e.g. by the ppc jit backend) */
rpy_stacktoobig_t rpy_stacktoobig = {
    NULL,             /* stack_end */
    MAX_STACK_SIZE,   /* stack_length */
    1                 /* report_error */
};

static Signed _ll_stack_os_limit(void)
{
	/* Size in bytes of this thread's C stack as the OS sees it, or 0 if
	   unknown/unlimited.  Computed once and cached: this is not on a hot
	   path (LL_stack_set_length_fraction is only called when the recursion
	   limit changes), but infinite_recursion() toggles the limit in a loop,
	   so caching keeps repeated calls free.  The cache matches the existing
	   single-global design of rpy_stacktoobig (already main-thread-centric);
	   a benign race just recomputes the same value. */
	static Signed cached = -1;
	if (cached != -1)
		return cached;
	cached = 0;
#ifdef _WIN32
#  if defined(_WIN32_WINNT) && _WIN32_WINNT >= 0x0602
	{
		/* GetCurrentThreadStackLimits: Windows 8 / Server 2012+.  On older
		   targets we fall back to no clamp, like CPython 3.12 which uses a
		   fixed Py_C_RECURSION_LIMIT on Windows rather than a runtime query. */
		ULONG_PTR low, high;
		GetCurrentThreadStackLimits(&low, &high);
		cached = (Signed)(high - low);
	}
#  endif
#else
	{
		struct rlimit rl;
		if (getrlimit(RLIMIT_STACK, &rl) == 0 &&
		    rl.rlim_cur != RLIM_INFINITY && rl.rlim_cur != 0)
			cached = (Signed)rl.rlim_cur;
	}
#endif
	return cached;
}

void LL_stack_set_length_fraction(double fraction)
{
	Signed length = (Signed)(MAX_STACK_SIZE * fraction);
	/* sys.setrecursionlimit() scales 'length' linearly (length =
	   MAX_STACK_SIZE * limit/1000), so a high limit -- e.g.
	   test.support.infinite_recursion() sets it to ~20000 -- can push
	   'length' past the real OS stack and segfault before stack_check()
	   ever reports an overflow.  Clamp 'length' to the actual stack the OS
	   gives this thread, minus a 25% margin for the C frames between the
	   check and the guard page, so the check always fires first and we
	   raise RecursionError.  This decouples the hard C-stack guard from the
	   soft Python recursion limit, matching CPython's Py_C_RECURSION_LIMIT. */
	Signed os_limit = _ll_stack_os_limit();
	if (os_limit > 0) {
		Signed cap = os_limit - (os_limit >> 2);
		if (cap > 0 && length > cap)
			length = cap;
	}
	rpy_stacktoobig.stack_length = length;
}

char LL_stack_too_big_slowpath(Signed current)
{
	Signed diff, max_stack_size;
	char *baseptr, *curptr = (char*)current;
	char *tl;
	struct pypy_threadlocal_s *tl1;

	/* The stack_end variable is updated to match the current value
	   if it is still 0 or if we later find a 'curptr' position
	   that is above it.  The real stack_end pointer is stored in
	   thread-local storage, but we try to minimize its overhead by
	   keeping a local copy in rpy_stacktoobig.stack_end. */

	OP_THREADLOCALREF_ADDR(tl);
	tl1 = (struct pypy_threadlocal_s *)tl;
	baseptr = tl1->stack_end;
	max_stack_size = rpy_stacktoobig.stack_length;
	if (baseptr == NULL) {
		/* first time we see this thread */
	}
	else {
		diff = baseptr - curptr;
		if (((Unsigned)diff) <= (Unsigned)max_stack_size) {
			/* within bounds, probably just had a thread switch */
			rpy_stacktoobig.stack_end = baseptr;
			return 0;
		}
		if (((Unsigned)-diff) <= (Unsigned)max_stack_size) {
			/* stack underflowed: the initial estimation of
			   the stack base must be revised */
		}
		else {	/* stack overflow (probably) */
			return rpy_stacktoobig.report_error;
		}
	}

	/* update the stack base pointer to the current value */
	baseptr = curptr;
	tl1->stack_end = baseptr;
	rpy_stacktoobig.stack_end = baseptr;
	return 0;
}
