#include "qcgc.h"

#include <assert.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "allocator.h"
#include "hugeblocktable.h"
#include "event_logger.h"

void qcgc_mark(bool incremental);
void qcgc_pop_object(object_t *object);
void qcgc_push_object(object_t *object);
void qcgc_sweep(void);

void qcgc_initialize(void) {
	qcgc_state.shadow_stack = qcgc_shadow_stack_create(QCGC_SHADOWSTACK_SIZE);
	qcgc_state.prebuilt_objects = qcgc_shadow_stack_create(16); //XXX
	qcgc_state.gp_gray_stack = qcgc_gray_stack_create(16); // XXX
	qcgc_state.gray_stack_size = 0;
	qcgc_state.phase = GC_PAUSE;
	qcgc_allocator_initialize();
	qcgc_hbtable_initialize();
	qcgc_event_logger_initialize();
}

void qcgc_destroy(void) {
	qcgc_event_logger_destroy();
	qcgc_hbtable_destroy();
	qcgc_allocator_destroy();
	free(qcgc_state.shadow_stack);
	free(qcgc_state.prebuilt_objects);
	free(qcgc_state.gp_gray_stack);
}

/**
 * Shadow stack
 */
void qcgc_shadowstack_push(object_t *object) {
	if (qcgc_state.phase != GC_PAUSE) {
		qcgc_state.phase = GC_MARK;
		qcgc_push_object(object);
	}
	qcgc_state.shadow_stack =
		qcgc_shadow_stack_push(qcgc_state.shadow_stack, object);
}

object_t *qcgc_shadowstack_pop(void) {
	object_t *result = qcgc_shadow_stack_top(qcgc_state.shadow_stack);
	qcgc_state.shadow_stack = qcgc_shadow_stack_pop(qcgc_state.shadow_stack);
	return result;
}

/*******************************************************************************
 * Write barrier                                                               *
 ******************************************************************************/
void qcgc_write(object_t *object) {
#if CHECKED
	assert(object != NULL);
#endif
	if ((object->flags & QCGC_GRAY_FLAG) != 0) {
		// Already gray, skip
		return;
	}
	object->flags |= QCGC_GRAY_FLAG;

	// Register prebuilt object if necessary
	if (((object->flags & QCGC_PREBUILT_OBJECT) != 0) &&
			((object->flags & QCGC_PREBUILT_REGISTERED) == 0)) {
		object->flags |= QCGC_PREBUILT_REGISTERED;
		qcgc_state.prebuilt_objects = qcgc_shadow_stack_push(
				qcgc_state.prebuilt_objects, object);
	}

	if (qcgc_state.phase == GC_PAUSE) {
		return; // We are done
	}

	// Triggered barrier, we must not collect now
	qcgc_state.phase = GC_MARK;

	// Test reachability of object and push if neccessary
	if ((object->flags & QCGC_PREBUILT_OBJECT) != 0) {
		// NOTE: No mark test here, as prebuilt objects are always reachable
		// Push prebuilt object to general purpose gray stack
		qcgc_state.gp_gray_stack = qcgc_gray_stack_push(
				qcgc_state.gp_gray_stack, object);
	} else if ((object_t *) qcgc_arena_addr((cell_t *) object) == object) {
		if (qcgc_hbtable_is_marked(object)) {
			// Push huge block to general purpose gray stack
			qcgc_state.gp_gray_stack = qcgc_gray_stack_push(
					qcgc_state.gp_gray_stack, object);
		}
	} else {
		if (qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_BLACK) {
			// This was black before, push it to gray stack again
			arena_t *arena = qcgc_arena_addr((cell_t *) object);
			arena->gray_stack = qcgc_gray_stack_push(
					arena->gray_stack, object);
		}
	}
}

/*******************************************************************************
 * Allocation                                                                  *
 ******************************************************************************/

object_t *qcgc_allocate(size_t size) {
#if LOG_ALLOCATION
	qcgc_event_logger_log(EVENT_ALLOCATE_START, sizeof(size_t),
			(uint8_t *) &size);
#endif
	object_t *result;
	if (size <= 1<<QCGC_LARGE_ALLOC_THRESHOLD_EXP) {
		// Use bump / fit allocator
		if (true) { // FIXME: Implement reasonable switch
			result = qcgc_bump_allocate(size);
		} else {
			result = qcgc_fit_allocate(size);

			// Fallback to bump allocator
			if (result == NULL) {
				result = qcgc_bump_allocate(size);
			}
		}
	} else {
		// Use huge block allocator
		result = qcgc_large_allocate(size);
	}

#if LOG_ALLOCATION
	qcgc_event_logger_log(EVENT_ALLOCATE_DONE, sizeof(object_t *),
			(uint8_t *) &result);
#endif
	return result;
}

/*******************************************************************************
 * Collection                                                                  *
 ******************************************************************************/

mark_color_t qcgc_get_mark_color(object_t *object) {
#if CHECKED
	assert(object != NULL);
#endif
	blocktype_t blocktype = qcgc_arena_get_blocktype((cell_t *) object);
	bool gray = (object->flags & QCGC_GRAY_FLAG) == QCGC_GRAY_FLAG;
	if (blocktype == BLOCK_WHITE) {
		if (gray) {
			return MARK_COLOR_LIGHT_GRAY;
		} else {
			return MARK_COLOR_WHITE;
		}
	} else if(blocktype == BLOCK_BLACK) {
		if (gray) {
			return MARK_COLOR_DARK_GRAY;
		} else {
			return MARK_COLOR_BLACK;
		}
	} else {
		return MARK_COLOR_INVALID;
	}
}

void qcgc_mark(bool incremental) {
#if CHECKED
	assert(qcgc_state.phase == GC_PAUSE || qcgc_state.phase == GC_MARK);
#endif
	// FIXME: Log some more information
	qcgc_event_logger_log(EVENT_MARK_START, 0, NULL);

	if (qcgc_state.phase == GC_PAUSE) {
		qcgc_state.phase = GC_MARK;

		// If we do this for the first time, push all roots.
		// All further changes to the roots (new additions) will be added
		// by qcgc_shadowstack_push
		for (size_t i = 0; i < qcgc_state.shadow_stack->count; i++) {
			qcgc_push_object(qcgc_state.shadow_stack->items[i]);
		}

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

	// FIXME: Log some more information
	qcgc_event_logger_log(EVENT_MARK_DONE, 0, NULL);
#if CHECKED
	assert(incremental || (qcgc_state.phase = GC_COLLECT));
	assert(qcgc_state.phase != GC_PAUSE);
#endif
}

void qcgc_pop_object(object_t *object) {
#if CHECKED
	assert(object != NULL);
	assert((object->flags & QCGC_GRAY_FLAG) == QCGC_GRAY_FLAG);
	if (((object->flags & QCGC_PREBUILT_OBJECT) == 0) &&
		((object_t *) qcgc_arena_addr((cell_t *) object) != object)) {
		assert(qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_BLACK);
	}
#endif
	object->flags &= ~QCGC_GRAY_FLAG;
	qcgc_trace_cb(object, &qcgc_push_object);
#if CHECKED
	if (((object->flags & QCGC_PREBUILT_OBJECT) == 0) &&
		((object_t *) qcgc_arena_addr((cell_t *) object) != object)) {
		assert(qcgc_get_mark_color(object) == MARK_COLOR_BLACK);
	}
#endif
}

void qcgc_push_object(object_t *object) {
#if CHECKED
	size_t old_stack_size = qcgc_state.gray_stack_size;
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
#if CHECKED
	if (object != NULL) {
		if (old_stack_size == qcgc_state.gray_stack_size) {
			assert(qcgc_get_mark_color(object) == MARK_COLOR_BLACK ||
					qcgc_get_mark_color(object) == MARK_COLOR_DARK_GRAY);
		} else {
			assert(qcgc_state.gray_stack_size == old_stack_size + 1);
			assert(qcgc_get_mark_color(object) == MARK_COLOR_DARK_GRAY);
		}
	} else {
		assert(old_stack_size == qcgc_state.gray_stack_size);
	}
#endif
}

void qcgc_sweep(void) {
#if CHECKED
	assert(qcgc_state.phase == GC_COLLECT);
#endif
	unsigned long arena_count;
	arena_count = qcgc_allocator_state.arenas->count;
	qcgc_event_logger_log(EVENT_SWEEP_START, sizeof(arena_count),
			(uint8_t *) &arena_count);

	qcgc_hbtable_sweep();
	size_t i = 0;
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

	qcgc_event_logger_log(EVENT_SWEEP_DONE, 0, NULL);
}

void qcgc_collect(void) {
	qcgc_mark(false);
	qcgc_sweep();
}
