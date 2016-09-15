#include "arena.h"

#include <assert.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>

#if DEBUG_ZERO_ON_SWEEP
#include <string.h>
#endif

#include "allocator.h"
#include "event_logger.h"
#include "gc_state.h"
#include "object_stack.h"

arena_t *qcgc_arena_create(void) {
	qcgc_event_logger_log(EVENT_NEW_ARENA, 0, NULL);

	arena_t *result;
	// Linux: MAP_ANONYMOUS is initialized to zero
	cell_t *mem = (cell_t *) mmap(0, 2 * QCGC_ARENA_SIZE,
			PROT_READ | PROT_WRITE,
			MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
	if (mem == MAP_FAILED) {
		// ERROR: OUT OF MEMORY
		return NULL;
	}
	if (mem != qcgc_arena_addr(mem)->cells) {
		// Not aligned -> align
		cell_t *aligned_mem = (cell_t *)(
				(intptr_t) qcgc_arena_addr(mem) + QCGC_ARENA_SIZE);
		size_t size_before = (size_t)((intptr_t) aligned_mem - (intptr_t) mem);
		size_t size_after = QCGC_ARENA_SIZE - size_before;

		munmap((void *) mem, size_before);
		munmap((void *)((intptr_t) aligned_mem + QCGC_ARENA_SIZE), size_after);
		result = (arena_t *) aligned_mem;
	} else {
		// free second half
		munmap((void *)((intptr_t) mem + QCGC_ARENA_SIZE), QCGC_ARENA_SIZE);
		result = (arena_t *) mem;
	}

	// Init bitmaps: One large free block
	result->mark_bitmap[QCGC_ARENA_FIRST_CELL_INDEX / 8] = 1;

	// Create gray stack
	result->gray_stack = qcgc_object_stack_create(QCGC_GRAY_STACK_INIT_SIZE);
	return result;
}

void qcgc_arena_destroy(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	free(arena->gray_stack);
	munmap((void *) arena, QCGC_ARENA_SIZE);
}

void qcgc_arena_mark_allocated(cell_t *ptr, size_t cells) {
	size_t index = qcgc_arena_cell_index(ptr);
	arena_t *arena = qcgc_arena_addr(ptr);
#if CHECKED
	assert(qcgc_arena_get_blocktype(arena, index) == BLOCK_FREE);
	for (size_t i = 1; i < cells; i++) {
		assert(qcgc_arena_get_blocktype(arena, index + i) == BLOCK_EXTENT);
	}
#endif
	qcgc_arena_set_blocktype(arena, index, BLOCK_WHITE);
	size_t index_of_next_block = index + cells;
	if (index_of_next_block < QCGC_ARENA_CELLS_COUNT &&
			qcgc_arena_get_blocktype(arena, index_of_next_block) ==
			BLOCK_EXTENT) {
		qcgc_arena_set_blocktype(arena, index_of_next_block, BLOCK_FREE);
	}
#if CHECKED
	assert(qcgc_arena_get_blocktype(arena, index) == BLOCK_WHITE);
	for (size_t i = 1; i < cells; i++) {
		assert(qcgc_arena_get_blocktype(arena, index + i) == BLOCK_EXTENT);
	}
	if (index_of_next_block < QCGC_ARENA_CELLS_COUNT) {
		assert(qcgc_arena_get_blocktype(arena, index + cells) != BLOCK_EXTENT);
	}
#endif
}

void qcgc_arena_mark_free(cell_t *ptr) {
	qcgc_arena_set_blocktype(qcgc_arena_addr(ptr), qcgc_arena_cell_index(ptr),
			BLOCK_FREE);
	// No coalescing, collector will do this
}

bool qcgc_arena_pseudo_sweep(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
	assert(qcgc_arena_is_coalesced(arena));
	assert(qcgc_arena_addr(_qcgc_bump_allocator.ptr) == arena);
#endif
	// Ignore free cell / largest block counting here, as blocks are not
	// registerd in free lists as well
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_BLACK:
				qcgc_arena_set_blocktype(arena, cell, BLOCK_WHITE);
			case BLOCK_FREE: // Fall through
			case BLOCK_EXTENT: // Fall through
			case BLOCK_WHITE: // Fall through
				break;
		}
	}
#if CHECKED
	assert(qcgc_arena_is_coalesced(arena));
#endif
	return false;
}

bool qcgc_arena_sweep(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
	assert(qcgc_arena_is_coalesced(arena));
#endif
	if (qcgc_arena_addr(_qcgc_bump_allocator.ptr) == arena) {
		return qcgc_arena_pseudo_sweep(arena);
	}

	size_t last_free_cell = 0;
	bool free = true;

	// Vectorized bitmap updates
	for (size_t i = QCGC_ARENA_FIRST_CELL_INDEX / 8;
			i < QCGC_ARENA_BITMAP_SIZE;
			i++) {
		uint8_t new_block = arena->block_bitmap[i] & arena->mark_bitmap[i];
		uint8_t new_mark = arena->block_bitmap[i] ^ arena->mark_bitmap[i];

		arena->block_bitmap[i] = new_block;

		if (new_block == new_mark) {
			// Both are 0
			continue;
		}

		if (!new_block) {
			// Only entries in the mark bitmap
			if (last_free_cell != 0) {
				// Coalesce
				new_mark = 0;
			} else {
				uint8_t first = __builtin_ctz(new_mark);
				new_mark = 1 << first;
				last_free_cell = i * 8 + first;
			}
		} else {
			for (size_t j = 0; j < 8; j++) {
				size_t cell = i * 8 + j;
				uint8_t m = (new_mark >> j) & 0x1;
				uint8_t b = (new_block >> j) & 0x1;
				uint8_t mask = 1 << j;
				if (m) {
					// Free
					if (last_free_cell != 0) {
						// Coalesce
						new_mark &= ~mask;
					} else {
						last_free_cell = cell;
					}
				} else if (b) {
					// White
					free = false;
					if (last_free_cell != 0) {
						qcgc_fit_allocator_add(arena->cells + last_free_cell,
								cell - last_free_cell);
#if DEBUG_ZERO_ON_SWEEP
						memset(arena->cells + last_free_cell, 0,
								sizeof(cell_t) * (cell - last_free_cell));
#endif
						qcgc_state.largest_free_block = MAX(
								qcgc_state.largest_free_block,
								cell - last_free_cell);
						last_free_cell = 0;
					}
				}
			}
		}
		arena->mark_bitmap[i] = new_mark;
	}

	if (last_free_cell != 0 && !free) {
		qcgc_fit_allocator_add(arena->cells + last_free_cell,
				QCGC_ARENA_CELLS_COUNT - last_free_cell);
#if DEBUG_ZERO_ON_SWEEP
		memset(arena->cells + last_free_cell, 0,
				sizeof(cell_t) * (QCGC_ARENA_CELLS_COUNT - last_free_cell));
#endif
		qcgc_state.largest_free_block = MAX(
				qcgc_state.largest_free_block,
				QCGC_ARENA_CELLS_COUNT - last_free_cell);
	}
#if CHECKED
	assert(qcgc_arena_is_coalesced(arena));
	assert(free == qcgc_arena_is_empty(arena));
#endif
	return free;
}

bool qcgc_arena_is_empty(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_WHITE: // Fall through
			case BLOCK_BLACK:
				return false;

			default:
				break;
		}
	}
	return true;
}


bool qcgc_arena_is_coalesced(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	bool prev_was_free = false;
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_WHITE: // Fall through
			case BLOCK_BLACK:
				prev_was_free = false;
				break;

			case BLOCK_FREE:
				if (prev_was_free) {
					return false;
				} else {
					prev_was_free = true;
				}
				break;

			case BLOCK_EXTENT:
				break;
		}
	}
	return true;
}

size_t qcgc_arena_free_blocks(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	size_t result = 0;
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_WHITE: // Fall through
			case BLOCK_BLACK:
			case BLOCK_EXTENT:
				break;

			case BLOCK_FREE:
				result++;
				break;
		}
	}
	return result;
}

size_t qcgc_arena_white_blocks(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	size_t result = 0;
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_BLACK:	// Fall through
			case BLOCK_EXTENT:
			case BLOCK_FREE:
				break;

			case BLOCK_WHITE:
				result++;
				break;
		}
	}
	return result;
}

size_t qcgc_arena_black_blocks(arena_t *arena) {
#if CHECKED
	assert(arena != NULL);
#endif
	size_t result = 0;
	for (size_t cell = QCGC_ARENA_FIRST_CELL_INDEX;
			cell < QCGC_ARENA_CELLS_COUNT;
			cell++) {
		switch (qcgc_arena_get_blocktype(arena, cell)) {
			case BLOCK_WHITE: // Fall through
			case BLOCK_FREE:
			case BLOCK_EXTENT:
				break;

			case BLOCK_BLACK:
				result++;
				break;
		}
	}
	return result;
}
