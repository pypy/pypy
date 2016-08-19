#pragma once

#define CHECKED 1							// Enable runtime sanity checks

#define QCGC_INIT_ZERO 1					// Init new objects with zero bytes

/**
 * Event logger
 */
#define EVENT_LOG 1							// Enable event log
#define LOGFILE "./qcgc_events.log"			// Default logfile
#define LOG_ALLOCATION 0					// Enable allocation log (warning:
											// significant performance impact)

#define QCGC_SHADOWSTACK_SIZE 128			// Number of initial entries for
											// shadow stack
#define QCGC_ARENA_BAG_INIT_SIZE 16			// Initial size of the arena bag
#define QCGC_ARENA_SIZE_EXP 20				// Between 16 (64kB) and 20 (1MB)
#define QCGC_LARGE_ALLOC_THRESHOLD 1<<14
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
 * DO NOT MODIFY BELOW HERE
 */

#ifdef TESTING
#define QCGC_STATIC
#else
#define QCGC_STATIC static
#endif
