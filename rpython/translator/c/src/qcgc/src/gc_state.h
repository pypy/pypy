#pragma once

#include "../qcgc.h"

#include <stddef.h>

#include "bag.h"
#include "gray_stack.h"
#include "shadow_stack.h"

/**
 * @typedef gc_state_t
 * Garbage collection states.
 * - GC_PAUSE	No gc in progress
 * - GC_MARK	Currently marking
 * - GC_COLLECT	Currently collecting
 */
typedef enum gc_phase {
	GC_PAUSE,
	GC_MARK,
	GC_COLLECT,
} gc_phase_t;

/**
 * @var qcgc_state
 *
 * Global state of the garbage collector
 */
struct qcgc_state {
	shadow_stack_t *prebuilt_objects;
	weakref_bag_t *weakrefs;
	gray_stack_t *gp_gray_stack;
	size_t gray_stack_size;
	gc_phase_t phase;

	size_t bytes_since_incmark;
	size_t incmark_since_sweep;
	size_t incmark_threshold;
	size_t incmark_to_sweep;

	size_t free_cells;			// Overall amount of free cells without huge
								// blocks and free areans. Valid right after sweep
	size_t largest_free_block;	// Size of the largest free block.
								// (Free arenas don't count as free blocks)
								// Valid right after sweep
} qcgc_state;
