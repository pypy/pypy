/* -*- c-basic-offset: 2 -*- */

/* XXX assumes that time never wraps around (in a 'long'), which may be
 * correct on 64-bit machines but not on 32-bit machines if the process
 * runs for long enough.
 *
 * XXX measure the overhead of the global_timestamp
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#define USE_PTHREAD_MUTEX    /* can be made optional */
#ifdef USE_PTHREAD_MUTEX
# include <pthread.h>
#endif

#include "src_stm/et.h"
#include "src_stm/atomic_ops.h"

#ifdef PYPY_STANDALONE         /* obscure: cannot include debug_print.h if compiled */
# define RPY_STM_DEBUG_PRINT   /* via ll2ctypes; only include it in normal builds */
# include "src/debug_print.h"
#else
# define RPY_STM_ASSERT    1
#endif

#ifdef RPY_STM_ASSERT
# include <assert.h>
#else
# undef assert
# define assert(x) /* nothing */
#endif

/************************************************************/

/* This is the same as the object header structure HDR
 * declared in stmgc.py */

typedef struct pypy_header0 orec_t;

/************************************************************/

#define IS_LOCKED(num)  ((num) < 0)
#define IS_LOCKED_OR_NEWER(num, max_age) \
  __builtin_expect(((unsigned long)(num)) > ((unsigned long)(max_age)), 0)

typedef long owner_version_t;

#define get_orec(addr)  ((volatile orec_t *)(addr))

/************************************************************/

#include "src_stm/lists.c"
#include "src_stm/core.c"
#include "src_stm/rpyintf.c"

/************************************************************/
