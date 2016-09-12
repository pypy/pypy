#include "collector.h"

#include <assert.h>
#include <stddef.h>

#include "arena.h"
#include "allocator.h"
#include "gc_state.h"
#include "event_logger.h"
#include "hugeblocktable.h"
#include "weakref.h"

QCGC_STATIC QCGC_INLINE void qcgc_pop_object(object_t *object);
QCGC_STATIC QCGC_INLINE void qcgc_push_object(object_t *object);

QCGC_STATIC void qcgc_mark(bool incremental) {
	{
		struct log_info_s {
			bool incremental;
			size_t gray_stack_size;
		};
		struct log_info_s log_info = {incremental, qcgc_state.gray_stack_size};
		qcgc_event_logger_log(EVENT_MARK_START, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}

	qcgc_state.bytes_since_incmark = 0;

	if (qcgc_state.phase == GC_PAUSE) {

		// If we do this for the first time, push all prebuilt objects.
		// All further changes to prebuilt objects will go to the gp_gray_stack
		// because of the write barrier
		size_t count = qcgc_state.prebuilt_objects->count;
		for (size_t i = 0; i < count; i++) {
			qcgc_state.gp_gray_stack = qcgc_gray_stack_push(
					qcgc_state.gp_gray_stack,
					qcgc_state.prebuilt_objects->items[i]);
		}
	}

	qcgc_state.phase = GC_MARK;

	// Always push all roots to make shadowstack pushes faster
	for (object_t **it = qcgc_state.shadow_stack_base;
		it < qcgc_state.shadow_stack;
		it++) {
		qcgc_push_object(*it);
	}

	while (qcgc_state.gray_stack_size > 0) {
		// General purpose gray stack (prebuilt objects and huge blocks)
		size_t to_process = (incremental ?
			MIN(qcgc_state.gp_gray_stack->index,
					MAX(qcgc_state.gp_gray_stack->index / 2, QCGC_INC_MARK_MIN)) :
			(qcgc_state.gp_gray_stack->index));

		while (to_process > 0) {
			object_t *top = qcgc_gray_stack_top(qcgc_state.gp_gray_stack);
			qcgc_state.gp_gray_stack = qcgc_gray_stack_pop(
					qcgc_state.gp_gray_stack);
			qcgc_pop_object(top);
			to_process--;
		}

		// Arena gray stacks
		for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
			arena_t *arena = qcgc_allocator_state.arenas->items[i];
			to_process = (incremental ?
					MIN(arena->gray_stack->index,
						MAX(arena->gray_stack->index / 2, QCGC_INC_MARK_MIN)) :
					(arena->gray_stack->index));

			while (to_process > 0) {
				object_t *top = qcgc_gray_stack_top(arena->gray_stack);
				arena->gray_stack = qcgc_gray_stack_pop(arena->gray_stack);
				qcgc_pop_object(top);
				to_process--;
			}
		}

		if (incremental) {
			break; // Execute loop once for incremental collection
		}
	}

	if (qcgc_state.gray_stack_size == 0) {
		qcgc_state.phase = GC_COLLECT;
	}

	{
		struct log_info_s {
			bool incremental;
			size_t gray_stack_size;
		};
		struct log_info_s log_info = {incremental, qcgc_state.gray_stack_size};
		qcgc_event_logger_log(EVENT_MARK_DONE, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}
#if CHECKED
	assert(incremental || (qcgc_state.phase = GC_COLLECT));
	assert(qcgc_state.phase != GC_PAUSE);
#endif
}

void qcgc_pop_object(object_t *object) {
#if CHECKED
	assert(object != NULL);
	assert((object->flags & QCGC_PREBUILT_OBJECT) == QCGC_PREBUILT_OBJECT ||
			(object->flags & QCGC_GRAY_FLAG) == QCGC_GRAY_FLAG);
	if (((object->flags & QCGC_PREBUILT_OBJECT) == 0) &&
		((object_t *) qcgc_arena_addr((cell_t *) object) != object)) {
		assert(qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_BLACK);
	}
#endif
	object->flags &= ~QCGC_GRAY_FLAG;
	qcgc_trace_cb(object, &qcgc_push_object);
}

QCGC_STATIC void qcgc_push_object(object_t *object) {
#if CHECKED
	assert(qcgc_state.phase == GC_MARK);
#endif
	if (object != NULL) {
		if ((object_t *) qcgc_arena_addr((cell_t *) object) == object) {
			if (qcgc_hbtable_mark(object)) {
				// Did mark it / was white before
				object->flags |= QCGC_GRAY_FLAG;
				qcgc_state.gp_gray_stack = qcgc_gray_stack_push(
						qcgc_state.gp_gray_stack, object);
			}
			return; // Skip tests
		}
		if ((object->flags & QCGC_PREBUILT_OBJECT) != 0) {
			return; // Prebuilt objects are always black, no pushing here
		}
		if (qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_WHITE) {
			object->flags |= QCGC_GRAY_FLAG;
			qcgc_arena_set_blocktype((cell_t *) object, BLOCK_BLACK);
			arena_t *arena = qcgc_arena_addr((cell_t *) object);
			arena->gray_stack = qcgc_gray_stack_push(arena->gray_stack, object);
		}
	}
}

void qcgc_sweep(void) {
#if CHECKED
	assert(qcgc_state.phase == GC_COLLECT);
#endif
	{
		unsigned long arena_count;
		arena_count = qcgc_allocator_state.arenas->count;
		qcgc_event_logger_log(EVENT_SWEEP_START, sizeof(arena_count),
				(uint8_t *) &arena_count);
	}

	qcgc_hbtable_sweep();
	size_t i = 0;
	qcgc_state.free_cells = 0;
	qcgc_state.largest_free_block = 0;

	qcgc_fit_allocator_empty_lists();
	while (i < qcgc_allocator_state.arenas->count) {
		arena_t *arena = qcgc_allocator_state.arenas->items[i];
		// The arena that contains the bump pointer is autmatically skipped
		if (qcgc_arena_sweep(arena)) {
			// Free
			qcgc_allocator_state.arenas = qcgc_arena_bag_remove_index(
					qcgc_allocator_state.arenas, i);
			qcgc_allocator_state.free_arenas = qcgc_arena_bag_add(
					qcgc_allocator_state.free_arenas, arena);
			// NO i++
		} else {
			// Not free
			i++;
		}
	}
	qcgc_state.phase = GC_PAUSE;

	// Determine whether fragmentation is too high
	// Fragmenation = 1 - (largest block / total free space)
	// Use bump allocator when fragmentation < 50%
	qcgc_allocator_state.use_bump_allocator = qcgc_state.free_cells <
		2 * qcgc_state.largest_free_block;

	update_weakrefs();

	{
		struct log_info_s {
			size_t free_cells;
			size_t largest_free_block;
		};
		struct log_info_s log_info = {
			qcgc_state.free_cells,
			qcgc_state.largest_free_block
		};
		qcgc_event_logger_log(EVENT_SWEEP_DONE, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}
}

