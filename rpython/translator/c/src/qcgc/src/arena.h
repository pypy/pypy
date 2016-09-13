/**
 * @file	arena.h
 */

#pragma once

#include "../qcgc.h"

#include <stdbool.h>
#include <sys/types.h>

#include "gray_stack.h"

#define QCGC_ARENA_SIZE (1<<QCGC_ARENA_SIZE_EXP)

#define QCGC_ARENA_BITMAP_SIZE (1<<(QCGC_ARENA_SIZE_EXP - 7)) // 1 / 128
#define QCGC_ARENA_CELLS_COUNT (1<<(QCGC_ARENA_SIZE_EXP - 4))

#define QCGC_ARENA_FIRST_CELL_INDEX (1<<(QCGC_ARENA_SIZE_EXP - 10))

/**
 * @typedef cell_t
 * The smallest unit of memory that can be addressed and allocated in arenas.
 */
typedef uint8_t cell_t[16];

/**
 * @typedef arena_t
 * Arena object
 */
typedef union {
	struct {
		union {
			gray_stack_t *gray_stack;
			uint8_t block_bitmap[QCGC_ARENA_BITMAP_SIZE];
		};
		uint8_t mark_bitmap[QCGC_ARENA_BITMAP_SIZE];
	};
	cell_t cells[QCGC_ARENA_CELLS_COUNT];
} arena_t;

/**
 * @typedef blocktype_t
 * Blocktypes:
 * - BLOCK_EXTENT	Extension of previous block
 * - BLOCK_FREE		Free block
 * - BLOCK_WHITE	Allocated block, marked white
 * - BLOCK_BLACK	Allocated block, marked black
 */
typedef enum blocktype {
	BLOCK_EXTENT,
	BLOCK_FREE,
	BLOCK_WHITE,
	BLOCK_BLACK,
} blocktype_t;

/**
 * Create a new arena.
 *
 * @return Pointer to new arena, NULL in case of errors
 */
arena_t *qcgc_arena_create(void);

/**
 * Destroys an arena (return to OS).
 *
 * @param	arena	The arena to destroy
 */
void qcgc_arena_destroy(arena_t *arena);

/**
 * Mark ptr as allocated area with given size.
 * DEPRECATED
 *
 * @param	ptr		Pointer to first cell of area
 * @param	cells	Size in cells
 */
void qcgc_arena_mark_allocated(cell_t *ptr, size_t cells);

/**
 * Mark cell ptr point to as free (no coalescing).
 * DEPRECATED
 *
 * @param	ptr		Pointer to cell that should be marked as free
 */
void qcgc_arena_mark_free(cell_t *ptr);

/**
 * Sweep given arena.
 *
 * @param	arena	Arena
 * @return	Whether arena is empty after sweeping
 */
bool qcgc_arena_sweep(arena_t *arena);

/**
 * Sweep given arena, but only reset black to white, no white to free
 *
 * @param	arena	Arena
 * @return	Whether arena is empty after sweeping, always false
 */
bool qcgc_arena_pseudo_sweep(arena_t *arena);


/*******************************************************************************
 * Inline functions
 ******************************************************************************/

/**
 * Arena pointer for given cell.
 *
 * @param	ptr		Pointer to cell for which you want to know the corresponding
 *					arena
 * @return	The arena the pointer belongs to
 */
QCGC_STATIC QCGC_INLINE arena_t *qcgc_arena_addr(cell_t *ptr) {
	return (arena_t *)((intptr_t) ptr & ~(QCGC_ARENA_SIZE - 1));
}

/**
 * Index of cell in arena.
 *
 * @param	ptr		Pointer to cell for which you want to know the cell index
 * @return	Index of the cell to which ptr points to
 */
QCGC_STATIC QCGC_INLINE size_t qcgc_arena_cell_index(cell_t *ptr) {
	return (size_t)((intptr_t) ptr & (QCGC_ARENA_SIZE - 1)) >> 4;
}

/**
 * Get blocktype.
 *
 * @param	arena		Arena in which to perform the lookup
 * @param	index		Cell index of the block to look up
 * @return	Blocktype
 */
QCGC_STATIC QCGC_INLINE blocktype_t qcgc_arena_get_blocktype(arena_t *arena,
		size_t index) {
#if CHECKED
	assert(arena != NULL);
	assert(index >= QCGC_ARENA_FIRST_CELL_INDEX);
	assert(index < QCGC_ARENA_CELLS_COUNT);
#endif
	// Read bitmap entry
	size_t byte = index / 8;
	uint8_t mask = 0x01 << (index % 8);
	bool block_bit = ((arena->block_bitmap[byte] & mask) == mask);
	bool mark_bit  = ((arena->mark_bitmap[byte] & mask) == mask);

	if (block_bit) {
		if (mark_bit) {
			return BLOCK_BLACK;
		} else {
			return BLOCK_WHITE;
		}
	} else {
		if (mark_bit) {
			return BLOCK_FREE;
		} else {
			return BLOCK_EXTENT;
		}
	}
}

/**
 * Set blocktype.
 *
 * @param	ptr		Pointer to cell for which you want to set the blocktype
 * @param	type	Blocktype that should be set
 */
QCGC_STATIC QCGC_INLINE void qcgc_arena_set_blocktype(arena_t *arena,
		size_t index, blocktype_t type) {
#if CHECKED
	assert(arena != NULL);
	assert(index >= QCGC_ARENA_FIRST_CELL_INDEX);
	assert(index < QCGC_ARENA_CELLS_COUNT);
#endif
	size_t byte = index / 8;
	uint8_t mask = 0x1 << (index % 8);
	switch(type) {
		case BLOCK_EXTENT:
			arena->block_bitmap[byte] &= ~mask;
			arena->mark_bitmap[byte] &= ~mask;
			break;
		case BLOCK_FREE:
			arena->block_bitmap[byte] &= ~mask;
			arena->mark_bitmap[byte] |= mask;
			break;
		case BLOCK_WHITE:
			arena->block_bitmap[byte] |= mask;
			arena->mark_bitmap[byte] &= ~mask;
			break;
		case BLOCK_BLACK:
			arena->block_bitmap[byte] |= mask;
			arena->mark_bitmap[byte] |= mask;
			break;
	}
}

/*******************************************************************************
 * Debug functions                                                             *
 ******************************************************************************/

/**
 * Check whether arena is empty.
 *
 * @param	arena	Arena
 * @return	true iff given arena is empty
 */
bool qcgc_arena_is_empty(arena_t *arena);

/**
 * Check whether arena is coalesced (no consecutive free blocks).
 *
 * @param	arena	Arena
 * @return	true iff given arena is coalesced
 */
bool qcgc_arena_is_coalesced(arena_t *arena);

/**
 * Count free blocks.
 *
 * @param	arena	Arena
 * @return	Number of free blocks
 */
size_t qcgc_arena_free_blocks(arena_t *arena);

/**
 * Count white blocks.
 *
 * @param	arena	Arena
 * @return	Number of white blocks
 */
size_t qcgc_arena_white_blocks(arena_t *arena);

/**
 * Count black blocks.
 *
 * @param	arena	Arena
 * @return	Number of black blocks
 */
size_t qcgc_arena_black_blocks(arena_t *arena);
