#pragma once

#define CHECKED 0							// Enable runtime sanity checks
#define DEBUG_ZERO_ON_SWEEP 0				// Zero memory on sweep (debug only)

#define QCGC_INIT_ZERO 0					// Init new objects with zero bytes

/**
 * Event logger
 */
#define EVENT_LOG 1							// Enable event log
#define LOGFILE "./qcgc_events.log"			// Default logfile
#define LOG_ALLOCATION 1					// Enable allocation log
#define LOG_DUMP_FREELIST_STATS 1			// Dump freelist stats

#define QCGC_SHADOWSTACK_SIZE 163840		// Total shadowstack size
#define QCGC_ARENA_BAG_INIT_SIZE 16			// Initial size of the arena bag
#define QCGC_ARENA_SIZE_EXP 20				// Between 16 (64kB) and 20 (1MB)
#define QCGC_LARGE_ALLOC_THRESHOLD_EXP 14	// Less than QCGC_ARENA_SIZE_EXP
#define QCGC_MARK_LIST_SEGMENT_SIZE 64		// TODO: Tune for performance
#define QCGC_GRAY_STACK_INIT_SIZE 128		// TODO: Tune for performance
#define QCGC_INC_MARK_MIN 64				// TODO: Tune for performance

/**
 * Fit allocator
 */
#define QCGC_LARGE_FREE_LIST_FIRST_EXP 5	// First exponent of large free list
#define QCGC_LARGE_FREE_LIST_INIT_SIZE 4	// Initial size for large free lists
#define QCGC_SMALL_FREE_LIST_INIT_SIZE 16	// Initial size for small free lists

/**
 * Auto Mark/Collect
 */
#define QCGC_INCMARK_THRESHOLD (1<<(QCGC_ARENA_SIZE_EXP-4))
#define QCGC_INCMARK_TO_SWEEP 5

/**
 * DO NOT MODIFY BELOW HERE
 */

#if QCGC_LARGE_ALLOC_THRESHOLD_EXP >= QCGC_ARENA_SIZE_EXP
#error	"Inconsistent configuration. Huge block threshold must be smaller " \
		"than the arena size."
#endif

#ifdef TESTING
#define QCGC_STATIC
#define QCGC_INLINE
#else
#define QCGC_STATIC static
#define QCGC_INLINE inline __attribute((always_inline))
#endif

#define MAX(a,b) (((a)>(b))?(a):(b))
#define MIN(a,b) (((a)<(b))?(a):(b))
#define UNUSED(x) (void)(x)
#define LIKELY(x) __builtin_expect((x), 1)
#define UNLIKELY(x) __builtin_expect((x), 0)
