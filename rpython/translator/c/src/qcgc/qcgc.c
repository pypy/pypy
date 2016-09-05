#include "qcgc.h"

#include <assert.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "allocator.h"
#include "hugeblocktable.h"
#include "event_logger.h"

#define env_or_fallback(var, env_name, fallback) while(0) {		\
	char *env_val = getenv(env_name);							\
	if (env_val != NULL) {										\
		if (1 != sscanf(env_val, "%zu", &var)) {				\
			var = fallback;										\
		}														\
	}															\
}

void qcgc_mark(bool incremental);
void qcgc_pop_object(object_t *object);
void qcgc_push_object(object_t *object);
void qcgc_sweep(void);

static size_t major_collection_threshold = QCGC_MAJOR_COLLECTION_THRESHOLD;
static size_t incmark_threshold = QCGC_INCMARK_THRESHOLD;

QCGC_STATIC void update_weakrefs(void);

void qcgc_initialize(void) {
	qcgc_state.shadow_stack = qcgc_shadow_stack_create(QCGC_SHADOWSTACK_SIZE);
	qcgc_state.prebuilt_objects = qcgc_shadow_stack_create(16); // XXX
	qcgc_state.weakrefs = qcgc_weakref_bag_create(16); // XXX
	qcgc_state.gp_gray_stack = qcgc_gray_stack_create(16); // XXX
	qcgc_state.gray_stack_size = 0;
	qcgc_state.phase = GC_PAUSE;
	qcgc_state.bytes_since_collection = 0;
	qcgc_state.bytes_since_incmark = 0;
	qcgc_allocator_initialize();
	qcgc_hbtable_initialize();
	qcgc_event_logger_initialize();

	env_or_fallback(major_collection_threshold, "QCGC_MAJOR_COLLECTION",
			QCGC_MAJOR_COLLECTION_THRESHOLD);
	env_or_fallback(incmark_threshold, "QCGC_INCMARK", QCGC_INCMARK_THRESHOLD);
}

void qcgc_destroy(void) {
	qcgc_event_logger_destroy();
	qcgc_hbtable_destroy();
	qcgc_allocator_destroy();
	free(qcgc_state.shadow_stack);
	free(qcgc_state.prebuilt_objects);
	free(qcgc_state.weakrefs);
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

	if (qcgc_state.bytes_since_collection > major_collection_threshold) {
		qcgc_collect();
	}
	if (qcgc_state.bytes_since_incmark > incmark_threshold) {
		qcgc_mark(true);
	}

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

	// XXX: Should we use cells instead of bytes?
	qcgc_state.bytes_since_collection += size;
	qcgc_state.bytes_since_incmark += size;


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
	if (qcgc_state.phase == GC_COLLECT) {
		return;	// Fast exit when there is nothing to mark
	}
	// FIXME: Log some more information
	qcgc_event_logger_log(EVENT_MARK_START, 0, NULL);
	qcgc_state.bytes_since_incmark = 0;

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
	update_weakrefs();
}

void qcgc_collect(void) {
	qcgc_mark(false);
	qcgc_sweep();
	qcgc_state.bytes_since_collection = 0;
}

void qcgc_register_weakref(object_t *weakrefobj, object_t **target) {
#if CHECKED
	assert((weakrefobj->flags & QCGC_PREBUILT_OBJECT) == 0);
	assert((object_t *) qcgc_arena_addr((cell_t *) weakrefobj) != weakrefobj);
#endif
	// NOTE: At this point, the target must point to a pointer to a valid
	// object. We don't register any weakrefs to prebuilt objects as they
	// are always valid.
	if (((*target)->flags & QCGC_PREBUILT_OBJECT) == 0) {
		qcgc_state.weakrefs = qcgc_weakref_bag_add(qcgc_state.weakrefs,
				(struct weakref_bag_item_s) {
					.weakrefobj = weakrefobj,
					.target = target});
	}
}

QCGC_STATIC void update_weakrefs(void) {
	size_t i = 0;
	while (i < qcgc_state.weakrefs->count) {
		struct weakref_bag_item_s item = qcgc_state.weakrefs->items[i];
		// Check whether weakref object itself was collected
		// We know the weakref object is a normal object
		switch(qcgc_arena_get_blocktype((cell_t *) item.weakrefobj)) {
			case BLOCK_EXTENT: // Fall through
			case BLOCK_FREE:
				// Weakref itself was collected, forget it
				qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
						qcgc_state.weakrefs, i);
				continue;
			case BLOCK_BLACK:
			case BLOCK_WHITE:
				// Weakref object is still valid, continue
				break;
		}

		// Check whether the weakref target is still valid
		object_t *points_to = *item.target;
		if ((object_t *) qcgc_arena_addr((cell_t *) points_to) ==
				points_to) {
			// Huge object
			if (qcgc_hbtable_has(points_to)) {
				// Still valid
				i++;
			} else {
				// Invalid
				*(item.target) = NULL;
				qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
						qcgc_state.weakrefs, i);
			}
		} else {
			// Normal object
			switch(qcgc_arena_get_blocktype((cell_t *) points_to)) {
				case BLOCK_BLACK: // Still valid
				case BLOCK_WHITE:
					i++;
					break;
				case BLOCK_EXTENT: // Fall through
				case BLOCK_FREE:
					// Invalid
					*(item.target) = NULL;
					qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
							qcgc_state.weakrefs, i);
					break;
			}
		}
	}
}
