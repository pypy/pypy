/**
 * @file	arena.h
 */

#pragma once

#include "config.h"

#include <stdbool.h>
#include <stdint.h>
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
 * Arena pointer for given cell.
 *
 * @param	ptr		Pointer to cell for which you want to know the corresponding
 *					arena
 * @return	The arena the pointer belongs to
 */
arena_t *qcgc_arena_addr(cell_t *ptr);

/**
 * Index of cell in arena.
 *
 * @param	ptr		Pointer to cell for which you want to know the cell index
 * @return	Index of the cell to which ptr points to
 */
size_t qcgc_arena_cell_index(cell_t *ptr);

/**
 * Get bitmap value for given bitmap and cell index.
 *
 * @param	bitmap	Bitmap
 * @param	index	Index of cell
 * @return	true if bitmap entry is set, false otherwise
 */
bool qcgc_arena_get_bitmap_entry(uint8_t *bitmap, size_t index);

/**
 * Set bitmap value for given bitmap and cell index.
 *
 * @param	bitmap	Bitmap
 * @param	index	Index of cell
 * @param	value	true to set entry, false to reset entry
 */
void qcgc_arena_set_bitmap_entry(uint8_t *bitmap, size_t index, bool value);

/**
 * Get blocktype.
 *
 * @param	ptr		Pointer to cell for which you want to know the blocktype
 * @return	Blocktype
 */
blocktype_t qcgc_arena_get_blocktype(cell_t *ptr);

/**
 * Set blocktype.
 *
 * @param	ptr		Pointer to cell for which you want to set the blocktype
 * @param	type	Blocktype that should be set
 */
void qcgc_arena_set_blocktype(cell_t *ptr, blocktype_t type);

/**
 * Mark ptr as allocated area with given size.
 *
 * @param	ptr		Pointer to first cell of area
 * @param	cells	Size in cells
 */
void qcgc_arena_mark_allocated(cell_t *ptr, size_t cells);

/**
 * Mark cell ptr point to as free (no coalescing).
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
