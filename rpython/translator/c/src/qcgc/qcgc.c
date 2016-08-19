#include "qcgc.h"

#include <assert.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "allocator.h"
#include "event_logger.h"

// TODO: Eventually move to own header?
#define MAX(a,b) (((a)>(b))?(a):(b))
#define MIN(a,b) (((a)<(b))?(a):(b))

void qcgc_mark(void);
void qcgc_mark_all(void);
void qcgc_mark_incremental(void);
void qcgc_pop_object(object_t *object);
void qcgc_push_object(object_t *object);
void qcgc_sweep(void);

void qcgc_initialize(void) {
	qcgc_state.shadow_stack = qcgc_shadow_stack_create(QCGC_SHADOWSTACK_SIZE);
	qcgc_state.prebuilt_objects = qcgc_shadow_stack_create(16); //XXX
	qcgc_state.gray_stack_size = 0;
	qcgc_state.phase = GC_PAUSE;
	qcgc_allocator_initialize();
	qcgc_event_logger_initialize();
}

void qcgc_destroy(void) {
	qcgc_event_logger_destroy();
	qcgc_allocator_destroy();
	free(qcgc_state.shadow_stack);
}

/**
 * Shadow stack
 */
void qcgc_shadowstack_push(object_t *object) {
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
	if ((object->flags & QCGC_GRAY_FLAG) == 0) {
		object->flags |= QCGC_GRAY_FLAG;
		if ((object->flags & QCGC_PREBUILT_OBJECT) != 0) {
			// Save prebuilt object into list
			qcgc_shadow_stack_push(qcgc_state.prebuilt_objects, object);
		} else if (qcgc_state.phase != GC_PAUSE) {
			if (qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_BLACK) {
				// This was black before, push it to gray stack again
				arena_t *arena = qcgc_arena_addr((cell_t *) object);
				arena->gray_stack = qcgc_gray_stack_push(
						arena->gray_stack, object);
			}
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

	object_t *result = (object_t *) qcgc_allocator_allocate(size);
	result->flags |= QCGC_GRAY_FLAG;

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
#if CHECKED
		assert(false);
#endif
	}
}

void qcgc_mark(void) {
	qcgc_mark_all();
}

void qcgc_mark_all(void) {
#if CHECKED
	assert(qcgc_state.phase == GC_PAUSE || qcgc_state.phase == GC_MARK);
#endif
	qcgc_event_logger_log(EVENT_MARK_START, 0, NULL);

	qcgc_state.phase = GC_MARK;

	// Push all roots
	for (size_t i = 0; i < qcgc_state.shadow_stack->count; i++) {
		qcgc_push_object(qcgc_state.shadow_stack->items[i]);
	}

	// Trace all prebuilt objects
	for (size_t i = 0; i < qcgc_state.prebuilt_objects->count; i++) {
		qcgc_trace_cb(qcgc_state.prebuilt_objects->items[i], &qcgc_push_object);
	}

	while(qcgc_state.gray_stack_size > 0) {
		for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
			arena_t *arena = qcgc_allocator_state.arenas->items[i];
			while (arena->gray_stack->index > 0) {
				object_t *top =
					qcgc_gray_stack_top(arena->gray_stack);
				arena->gray_stack =
					qcgc_gray_stack_pop(arena->gray_stack);
				qcgc_pop_object(top);
			}
		}
	}

	qcgc_state.phase = GC_COLLECT;

	qcgc_event_logger_log(EVENT_MARK_DONE, 0, NULL);
}

void qcgc_mark_incremental(void) {
#if CHECKED
	assert(qcgc_state.phase == GC_PAUSE || qcgc_state.phase == GC_MARK);
#endif
	unsigned long gray_stack_size = qcgc_state.gray_stack_size;
	qcgc_event_logger_log(EVENT_INCMARK_START, sizeof(gray_stack_size),
			(uint8_t *) &gray_stack_size);

	qcgc_state.phase = GC_MARK;

	// Push all roots
	for (size_t i = 0; i < qcgc_state.shadow_stack->count; i++) {
		qcgc_push_object(qcgc_state.shadow_stack->items[i]);
	}

	// Trace all prebuilt objects
	for (size_t i = 0; i < qcgc_state.prebuilt_objects->count; i++) {
		qcgc_trace_cb(qcgc_state.prebuilt_objects->items[i], &qcgc_push_object);
	}

	for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
		arena_t *arena = qcgc_allocator_state.arenas->items[i];
		size_t initial_stack_size = arena->gray_stack->index;
		size_t to_process = MIN(arena->gray_stack->index,
				MAX(initial_stack_size / 2, QCGC_INC_MARK_MIN));
		while (to_process > 0) {
			object_t *top =
				qcgc_gray_stack_top(arena->gray_stack);
			arena->gray_stack =
				qcgc_gray_stack_pop(arena->gray_stack);
			qcgc_pop_object(top);
			to_process--;
		}
	}

	if (qcgc_state.gray_stack_size == 0) {
		qcgc_state.phase = GC_COLLECT;
	}

	gray_stack_size = qcgc_state.gray_stack_size;
	qcgc_event_logger_log(EVENT_INCMARK_START, sizeof(gray_stack_size),
			(uint8_t *) &gray_stack_size);
}

void qcgc_pop_object(object_t *object) {
#if CHECKED
	assert(object != NULL);
	assert((object->flags & QCGC_GRAY_FLAG) == QCGC_GRAY_FLAG);
	assert(qcgc_arena_get_blocktype((cell_t *) object) == BLOCK_BLACK);
#endif
	object->flags &= ~QCGC_GRAY_FLAG;
	qcgc_trace_cb(object, &qcgc_push_object);
#if CHECKED
	assert(qcgc_get_mark_color(object) == MARK_COLOR_BLACK);
#endif
}

void qcgc_push_object(object_t *object) {
#if CHECKED
	size_t old_stack_size = qcgc_state.gray_stack_size;
	assert(qcgc_state.phase == GC_MARK);
#endif
	if (object != NULL) {
		if ((object->flags & QCGC_PREBUILT_OBJECT) != 0) {
			return;
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

	for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
		qcgc_arena_sweep(qcgc_allocator_state.arenas->items[i]);
	}
	qcgc_state.phase = GC_PAUSE;

	qcgc_event_logger_log(EVENT_SWEEP_DONE, 0, NULL);
}

void qcgc_collect(void) {
	qcgc_mark();
	qcgc_sweep();
}
