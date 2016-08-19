#pragma once

#include "config.h"

#include <stddef.h>

#include "arena.h"
#include "bag.h"
#include "object.h"

/**
 * Free lists:
 *
 * Small free lists:
 *                +---+---+-----+----+
 * index:         | 0 | 1 | ... | 30 |
 *                +---+---+-----+----+
 * size (cells):  | 1 | 2 | ... | 31 |
 *                +---+---+-----+----+
 *
 * Large free lists:
 *                        +-----+-----+-----+---------+
 * index:                 |  0  |  1  | ... |    x    |
 *                        +-----+-----+-----+---------+
 * minimal size (cells):  | 2^5 | 2^6 | ... | 2^(x+5) |
 *                        +-----+-----+-----+---------+
 *
 * where x is chosen such that x + 5 + 1 = QCGC_ARENA_SIZE_EXP - 4 (i.e. the
 * next bin would hold chunks that have the size of at least one arena size,
 * which is impossible as an arena contains overhead)
 */

#define QCGC_LARGE_FREE_LISTS (QCGC_ARENA_SIZE_EXP - 4 - QCGC_LARGE_FREE_LIST_FIRST_EXP)

#define QCGC_SMALL_FREE_LISTS ((1<<QCGC_LARGE_FREE_LIST_FIRST_EXP) - 1)

struct qcgc_allocator_state {
	arena_bag_t *arenas;
	struct bump_state {
		cell_t *bump_ptr;
		size_t remaining_cells;
	} bump_state;
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
 * Allocate new memory region
 *
 * @param	bytes	Desired size of the memory region in bytes
 * @return	Pointer to memory large enough to hold size bytes, NULL in case of
 *			errors, already zero initialized if QCGC_INIT_ZERO is set
 */
cell_t *qcgc_allocator_allocate(size_t bytes);


/**
 * Add memory to free lists
 *
 * @param	ptr		Pointer to memory region
 * @param	cells	Size of memory region in cells
 */
void qcgc_fit_allocator_add(cell_t *ptr, size_t cells);
