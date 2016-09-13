#pragma once

#include "../qcgc.h"

#include "arena.h"
#include "bag.h"

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
	struct bump_state {
		cell_t *bump_ptr;
		size_t remaining_cells;
	} bump_state;
	struct fit_state {
		linear_free_list_t *small_free_list[QCGC_SMALL_FREE_LISTS];
		exp_free_list_t *large_free_list[QCGC_LARGE_FREE_LISTS];
	} fit_state;
	bool use_bump_allocator;
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
 * Allocate new memory region using bump allocator
 *
 * @param	bytes	Desired size of the memory region in bytes
 * @return	Pointer to memory large enough to hold size bytes, NULL in case of
 *			errors, already zero initialized if QCGC_INIT_ZERO is set
 */
object_t *qcgc_bump_allocate(size_t bytes);

/**
 * Allocate new memory region using huge block allocator
 *
 * @param	bytes	Desired size of the memory region in bytes
 * @return	Pointer to memory large enough to hold size bytes, NULL in case of
 *			errors, already zero initialized if QCGC_INIT_ZERO is set
 */
object_t *qcgc_large_allocate(size_t bytes);

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
