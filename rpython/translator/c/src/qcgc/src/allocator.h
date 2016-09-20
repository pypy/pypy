#pragma once

#include "../qcgc.h"

#include <string.h>
#include <stdlib.h>

#include "arena.h"
#include "bag.h"
#include "hugeblocktable.h"

/**
 * Free lists:
 *
 * Small free lists:
 *                +---+---+-----+----+
 * index:         | 0 | 1 | ... | 30 |
 *                +---+---+-----+----+
 * size (cells):  | 1 | 2 | ... | 31 |
 *                +---+---+-----+----+
 * (31 is 2^QCGC_LARGE_FREE_LIST_FIRST_EXP - 1)
 *
 * Large free lists:
 *                        +-----+-----+-----+---------+
 * index:                 |  0  |  1  | ... |    x    |
 *                        +-----+-----+-----+---------+
 * minimal size (cells):  | 2^5 | 2^6 | ... | 2^(x+5) |
 *                        +-----+-----+-----+---------+
 * (5 is QCGC_LARGE_FREE_LIST_FIRST_EXP)
 *
 * where x is chosen such that 2^(x + 5) = 2^QCGC_LARGE_ALLOC_THRESHOLD_EXP
 * (i.e. such that the last bin contains all blocks that are larger or equal
 * than the threshold for huge blocks. These blocks can be returned to the
 * bump allocator)
 */
#define QCGC_LARGE_FREE_LISTS (QCGC_LARGE_ALLOC_THRESHOLD_EXP - QCGC_LARGE_FREE_LIST_FIRST_EXP - 4 + 1)
// -4 because of turning bytes into cells, +1 because we start to count at 0

#define QCGC_SMALL_FREE_LISTS ((1<<QCGC_LARGE_FREE_LIST_FIRST_EXP) - 1)

struct qcgc_allocator_state {
	arena_bag_t *arenas;
	arena_bag_t *free_arenas;
	struct fit_state {
		linear_free_list_t *small_free_list[QCGC_SMALL_FREE_LISTS];
		exp_free_list_t *large_free_list[QCGC_LARGE_FREE_LISTS];
	} fit_state;
} qcgc_allocator_state;

/**
 * Initialize allocator
 */
void qcgc_allocator_initialize(void);

/**
 * Destroy allocator
 */
void qcgc_allocator_destroy(void);

/**
 * Allocate new memory region using fit allocator
 *
 * @param	bytes	Desired size of the memory region in bytes
 * @return	Pointer to memory large enough to hold size bytes, NULL in case of
 *			errors or if there is no block sufficently large block, already zero
 *			initialized if QCGC_INIT_ZERO is set
 */
object_t *qcgc_fit_allocate(size_t bytes);

/**
 * Empty all free lists (used before sweep)
 */
void qcgc_fit_allocator_empty_lists(void);

/**
 * Add memory to free lists
 *
 * @param	ptr		Pointer to memory region
 * @param	cells	Size of memory region in cells
 */
void qcgc_fit_allocator_add(cell_t *ptr, size_t cells);

/**
 * Reset bump pointer
 */
QCGC_STATIC QCGC_INLINE void qcgc_reset_bump_ptr(void) {
	if (_qcgc_bump_allocator.end > _qcgc_bump_allocator.ptr) {
		qcgc_arena_set_blocktype(
				qcgc_arena_addr(_qcgc_bump_allocator.ptr),
				qcgc_arena_cell_index(
					_qcgc_bump_allocator.ptr),
				BLOCK_FREE);
		qcgc_fit_allocator_add(_qcgc_bump_allocator.ptr,
				_qcgc_bump_allocator.end - _qcgc_bump_allocator.ptr);
	}
	_qcgc_bump_allocator.ptr = NULL;
	_qcgc_bump_allocator.end = NULL;
}

/**
 * Find a new block for the bump allocator
 *
 * @param	size		Minimal size
 * @param	force_arena	Force generation of new arena if no block is found
 */
void qcgc_bump_allocator_renew_block(size_t size, bool force_arena);
