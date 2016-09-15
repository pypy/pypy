#include "allocator.h"

#include <assert.h>
#include <stdbool.h>
#include "gc_state.h"

QCGC_STATIC QCGC_INLINE void bump_allocator_assign(cell_t *ptr, size_t cells);

QCGC_STATIC QCGC_INLINE bool is_small(size_t cells);
QCGC_STATIC QCGC_INLINE size_t small_index(size_t cells);
QCGC_STATIC QCGC_INLINE size_t large_index(size_t cells);
QCGC_STATIC QCGC_INLINE size_t small_index_to_cells(size_t index);

QCGC_STATIC cell_t *fit_allocator_small_first_fit(size_t index, size_t cells);
QCGC_STATIC cell_t *fit_allocator_large_fit(size_t index, size_t cells);
QCGC_STATIC cell_t *fit_allocator_large_first_fit(size_t index, size_t cells);

void qcgc_allocator_initialize(void) {
	qcgc_allocator_state.arenas =
		qcgc_arena_bag_create(QCGC_ARENA_BAG_INIT_SIZE);
	qcgc_allocator_state.free_arenas = qcgc_arena_bag_create(4); // XXX

	// Fit Allocator
	for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
		qcgc_allocator_state.fit_state.small_free_list[i] =
			qcgc_linear_free_list_create(QCGC_SMALL_FREE_LIST_INIT_SIZE);
	}

	for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
		qcgc_allocator_state.fit_state.large_free_list[i] =
			qcgc_exp_free_list_create(QCGC_LARGE_FREE_LIST_INIT_SIZE);
	}

	_qcgc_bump_allocator.ptr = NULL;
	_qcgc_bump_allocator.end = NULL;
	qcgc_bump_allocator_renew_block(true);
}

void qcgc_allocator_destroy(void) {
	// Fit Allocator
	for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
		free(qcgc_allocator_state.fit_state.small_free_list[i]);
	}

	for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
		free(qcgc_allocator_state.fit_state.large_free_list[i]);
	}

	// Arenas
	size_t arena_count = qcgc_allocator_state.arenas->count;
	for (size_t i = 0; i < arena_count; i++) {
		qcgc_arena_destroy(qcgc_allocator_state.arenas->items[i]);
	}

	arena_count = qcgc_allocator_state.free_arenas->count;
	for (size_t i = 0; i < arena_count; i++) {
		qcgc_arena_destroy(qcgc_allocator_state.free_arenas->items[i]);
	}

	free(qcgc_allocator_state.arenas);
	free(qcgc_allocator_state.free_arenas);
}

/*******************************************************************************
 * Bump Allocator                                                              *
 ******************************************************************************/

void qcgc_bump_allocator_renew_block(bool force_arena) {
#if CHECKED
	if (_qcgc_bump_allocator.end > _qcgc_bump_allocator.ptr) {
		for (cell_t *it = _qcgc_bump_allocator.ptr + 1;
				it < _qcgc_bump_allocator.end; it++) {
			assert(qcgc_arena_get_blocktype(qcgc_arena_addr(it),
						qcgc_arena_cell_index(it))
					== BLOCK_EXTENT);
		}
	}
#endif
	qcgc_reset_bump_ptr();

	// Always use a huge block if there is one
	exp_free_list_t *free_list = qcgc_allocator_state.fit_state.
		large_free_list[QCGC_LARGE_FREE_LISTS - 1];

	if (free_list->count > 0) {
		// Assign huge block to bump allocator
		bump_allocator_assign(free_list->items[0].ptr,
				free_list->items[0].size);
		free_list = qcgc_exp_free_list_remove_index(free_list, 0);
		qcgc_allocator_state.fit_state.
			large_free_list[QCGC_LARGE_FREE_LISTS - 1] = free_list;
		qcgc_state.free_cells -=
			_qcgc_bump_allocator.end - _qcgc_bump_allocator.ptr;
	} else {
		if (qcgc_allocator_state.free_arenas->count > 0) {
			// Reuse arena
			arena_t *arena = qcgc_allocator_state.free_arenas->items[0];
			qcgc_allocator_state.free_arenas = qcgc_arena_bag_remove_index(
					qcgc_allocator_state.free_arenas, 0);
			bump_allocator_assign(&(arena->cells[QCGC_ARENA_FIRST_CELL_INDEX]),
					QCGC_ARENA_CELLS_COUNT - QCGC_ARENA_FIRST_CELL_INDEX);
			qcgc_allocator_state.arenas =
				qcgc_arena_bag_add(qcgc_allocator_state.arenas, arena);
		} else {
			// FIXME: Nifty decision making whether to allocate new arena
			bool new_arena = false;
			if (force_arena || new_arena) {
				arena_t *arena = qcgc_arena_create();
				bump_allocator_assign(&(arena->cells[QCGC_ARENA_FIRST_CELL_INDEX]),
						QCGC_ARENA_CELLS_COUNT - QCGC_ARENA_FIRST_CELL_INDEX);
				qcgc_allocator_state.arenas =
					qcgc_arena_bag_add(qcgc_allocator_state.arenas, arena);
			}
		}
	}
#if CHECKED
	assert(!force_arena || _qcgc_bump_allocator.ptr != NULL);
	if (_qcgc_bump_allocator.ptr != NULL) {
		assert(qcgc_arena_get_blocktype(
					qcgc_arena_addr( _qcgc_bump_allocator.ptr),
					qcgc_arena_cell_index(
						_qcgc_bump_allocator.ptr))
				== BLOCK_FREE);
		for (cell_t *it = _qcgc_bump_allocator.ptr + 1;
				it < _qcgc_bump_allocator.end; it++) {
			assert(qcgc_arena_get_blocktype(qcgc_arena_addr(it),
						qcgc_arena_cell_index(it)) == BLOCK_EXTENT);
		}
	}
#endif
}

QCGC_STATIC void bump_allocator_assign(cell_t *ptr, size_t cells) {
#if CHECKED
	assert(qcgc_arena_get_blocktype(qcgc_arena_addr(ptr),
				qcgc_arena_cell_index(ptr)) == BLOCK_FREE);
	for (size_t i = 1; i < cells; i++) {
		assert(qcgc_arena_get_blocktype(qcgc_arena_addr(ptr + i),
					qcgc_arena_cell_index(ptr + i)) == BLOCK_EXTENT);
	}
#endif
	_qcgc_bump_allocator.ptr = ptr;
	_qcgc_bump_allocator.end = ptr + cells;
}

/*******************************************************************************
 * Fit Allocator                                                               *
 ******************************************************************************/

object_t *qcgc_fit_allocate(size_t bytes) {
#if CHECKED
	//free_list_consistency_check();
#endif
	size_t cells = bytes_to_cells(bytes);
	cell_t *mem;

	if (is_small(cells)) {
		size_t index = small_index(cells);
		mem = fit_allocator_small_first_fit(index, cells);
	} else {
		size_t index = large_index(cells);
		mem = fit_allocator_large_fit(index, cells);
	}

	if (mem == NULL) {
		return NULL;
	}

	object_t *result = (object_t *) mem;

#if QCGC_INIT_ZERO
	memset(result, 0, cells * sizeof(cell_t));
#endif

	qcgc_state.free_cells -= cells;
	result->flags = QCGC_GRAY_FLAG;
	return result;
}

void qcgc_fit_allocator_empty_lists(void) {
	for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
		qcgc_allocator_state.fit_state.small_free_list[i]->count = 0;
	}

	for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
		qcgc_allocator_state.fit_state.large_free_list[i]->count = 0;
	}
}

void qcgc_fit_allocator_add(cell_t *ptr, size_t cells) {
#if CHECKED
	assert(cells > 0);
#endif
	if (is_small(cells)) {
		size_t index = small_index(cells);
		qcgc_allocator_state.fit_state.small_free_list[index] =
			qcgc_linear_free_list_add(
					qcgc_allocator_state.fit_state.small_free_list[index],
					ptr);
	} else {
		size_t index = large_index(cells);
		qcgc_allocator_state.fit_state.large_free_list[index] =
			qcgc_exp_free_list_add(
					qcgc_allocator_state.fit_state.large_free_list[index],
					(struct exp_free_list_item_s) {ptr, cells});
	}
	qcgc_state.free_cells += cells;
}

QCGC_STATIC cell_t *fit_allocator_small_first_fit(size_t index, size_t cells) {
#if CHECKED
	assert(small_index_to_cells(index) >= cells);
#endif
	cell_t *result = NULL;
	for ( ; index < QCGC_SMALL_FREE_LISTS; index++) {
		size_t list_cell_size = small_index_to_cells(index);

		if (qcgc_allocator_state.fit_state.small_free_list[index]->count > 0) {
			result = qcgc_allocator_state.fit_state.small_free_list[index]->
				items[0];
			qcgc_allocator_state.fit_state.small_free_list[index] =
				qcgc_linear_free_list_remove_index(
						qcgc_allocator_state.fit_state.small_free_list[index],
						0);
			qcgc_arena_set_blocktype(qcgc_arena_addr(result),
					qcgc_arena_cell_index(result), BLOCK_WHITE);
			if (list_cell_size - cells > 0) {
				qcgc_arena_set_blocktype(qcgc_arena_addr(result + cells),
						qcgc_arena_cell_index(result + cells), BLOCK_FREE);
				qcgc_fit_allocator_add(result + cells, list_cell_size - cells);
				qcgc_state.free_cells -= list_cell_size - cells;
			}
			return result;
		}
	}
	return fit_allocator_large_first_fit(0, cells);
}

QCGC_STATIC cell_t *fit_allocator_large_fit(size_t index, size_t cells) {
#if CHECKED
	assert(1u<<(index + QCGC_LARGE_FREE_LIST_FIRST_EXP) <= cells);
	assert(1u<<(index + QCGC_LARGE_FREE_LIST_FIRST_EXP + 1) > cells);
#endif
	size_t best_fit_index = qcgc_allocator_state.fit_state.
		large_free_list[index]->count;

	cell_t *result = NULL;
	size_t best_fit_cells = SIZE_MAX;
	size_t count = qcgc_allocator_state.fit_state.large_free_list[index]->count;
	for (size_t i = 0; i < count; i++) {
		if (qcgc_allocator_state.fit_state.large_free_list[index]->
				items[i].size >= cells &&
				qcgc_allocator_state.fit_state.large_free_list[index]->
				items[i].size < best_fit_cells) {
			result = qcgc_allocator_state.fit_state.large_free_list[index]->
				items[i].ptr;
			best_fit_cells = qcgc_allocator_state.fit_state.
				large_free_list[index]->items[i].size;
			best_fit_index = i;
		}
		if (best_fit_cells == cells) {
			break;
		}
	}

	if (result != NULL) {
		// Best fit was found
		assert(best_fit_index < qcgc_allocator_state.fit_state.
				large_free_list[index]->count);
		qcgc_allocator_state.fit_state.large_free_list[index] =
			qcgc_exp_free_list_remove_index(qcgc_allocator_state.fit_state.
					large_free_list[index], best_fit_index);
		qcgc_arena_set_blocktype(qcgc_arena_addr(result),
				qcgc_arena_cell_index(result), BLOCK_WHITE);
		if (best_fit_cells - cells > 0) {
			qcgc_arena_set_blocktype(qcgc_arena_addr(result + cells),
					qcgc_arena_cell_index(result + cells), BLOCK_FREE);
			qcgc_fit_allocator_add(result + cells, best_fit_cells - cells);
			qcgc_state.free_cells -= best_fit_cells - cells;
		}
	} else {
		// No best fit, go for first fit
		result = fit_allocator_large_first_fit(index + 1, cells);
	}
	return result;
}

QCGC_STATIC cell_t *fit_allocator_large_first_fit(size_t index, size_t cells) {
#if CHECKED
	assert(1u<<(index + QCGC_LARGE_FREE_LIST_FIRST_EXP) >= cells);
#endif
	for ( ; index < QCGC_LARGE_FREE_LISTS; index++) {
		if (qcgc_allocator_state.fit_state.large_free_list[index]->count > 0) {
			struct exp_free_list_item_s item =
				qcgc_allocator_state.fit_state.large_free_list[index]->items[0];
			qcgc_allocator_state.fit_state.large_free_list[index] =
				qcgc_exp_free_list_remove_index(
						qcgc_allocator_state.fit_state.large_free_list[index],
						0);

			qcgc_arena_set_blocktype(qcgc_arena_addr(item.ptr),
					qcgc_arena_cell_index(item.ptr), BLOCK_WHITE);
			if (item.size - cells > 0) {
				qcgc_arena_set_blocktype(qcgc_arena_addr(item.ptr + cells),
						qcgc_arena_cell_index(item.ptr + cells), BLOCK_FREE);
				qcgc_fit_allocator_add(item.ptr + cells, item.size - cells);
				qcgc_state.free_cells -= item.size - cells;
			}
			return item.ptr;
		}
	}
	return NULL;
}

QCGC_STATIC QCGC_INLINE bool is_small(size_t cells) {
	return cells <= QCGC_SMALL_FREE_LISTS;
}

QCGC_STATIC QCGC_INLINE size_t small_index(size_t cells) {
#if CHECKED
	assert(is_small(cells));
#endif
	return cells - 1;
}

QCGC_STATIC QCGC_INLINE size_t large_index(size_t cells) {
#if CHECKED
	assert(!is_small(cells));
#endif
	// shift such that the meaningless part disappears, i.e. everything that
	// belongs into the first free list will become 1.
	cells = cells >> QCGC_LARGE_FREE_LIST_FIRST_EXP;

	// calculates floor(log(cells))
	return MIN((8 * sizeof(unsigned long)) - __builtin_clzl(cells) - 1,
			QCGC_LARGE_FREE_LISTS - 1);
}

QCGC_STATIC QCGC_INLINE size_t small_index_to_cells(size_t index) {
#if CHECKED
	assert(index < QCGC_SMALL_FREE_LISTS);
#endif
	return index + 1;
}
