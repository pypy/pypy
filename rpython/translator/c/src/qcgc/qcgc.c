#include "qcgc.h"

#include <assert.h>
#include <stdio.h>
#include <sys/mman.h>

#include "src/allocator.h"
#include "src/collector.h"
#include "src/event_logger.h"
#include "src/gc_state.h"
#include "src/hugeblocktable.h"
#include "src/signal_handler.h"

#define env_or_fallback(var, env_name, fallback) do {			\
	char *env_val = getenv(env_name);							\
	if (env_val != NULL) {										\
		if (1 != sscanf(env_val, "%zu", &var)) {				\
			var = fallback;										\
		}														\
	} else {													\
		var = fallback;											\
	}															\
} while(0)

QCGC_STATIC QCGC_INLINE void initialize_shadowstack(void);
QCGC_STATIC QCGC_INLINE void destroy_shadowstack(void);

void qcgc_initialize(void) {
	initialize_shadowstack();
	qcgc_state.prebuilt_objects = qcgc_object_stack_create(16); // XXX
	qcgc_state.weakrefs = qcgc_weakref_bag_create(16); // XXX
	qcgc_state.gp_gray_stack = qcgc_object_stack_create(16); // XXX
	qcgc_state.gray_stack_size = 0;
	qcgc_state.phase = GC_PAUSE;
	qcgc_state.cells_since_incmark = 0;
	qcgc_state.incmark_since_sweep = 0;
	qcgc_state.free_cells = 0;
	qcgc_state.largest_free_block = 0;
	qcgc_allocator_initialize();
	qcgc_hbtable_initialize();
	qcgc_event_logger_initialize();

	env_or_fallback(qcgc_state.incmark_threshold,
			"QCGC_INCMARK", QCGC_INCMARK_THRESHOLD);
	env_or_fallback(qcgc_state.incmark_to_sweep,
			"QCGC_INCMARK_TO_SWEEP", QCGC_INCMARK_TO_SWEEP);

	setup_signal_handler();
}

void qcgc_destroy(void) {
	qcgc_event_logger_destroy();
	qcgc_hbtable_destroy();
	qcgc_allocator_destroy();
	destroy_shadowstack();
	free(qcgc_state.prebuilt_objects);
	free(qcgc_state.weakrefs);
	free(qcgc_state.gp_gray_stack);
}

object_t *_qcgc_allocate_large(size_t size) {
#if CHECKED
	assert(size >= 1<<QCGC_LARGE_ALLOC_THRESHOLD_EXP);
#endif
	if (UNLIKELY(qcgc_state.cells_since_incmark >
				qcgc_state.incmark_threshold)) {
		if (qcgc_state.incmark_since_sweep == qcgc_state.incmark_to_sweep) {
			qcgc_collect();
		} else {
			qcgc_incmark();
			qcgc_state.incmark_since_sweep++;
		}
	}

	// FIXME: alligned_alloc requires size to be a multiple of the alignment
	object_t *result = aligned_alloc(QCGC_ARENA_SIZE, size);
#if QCGC_INIT_ZERO
	memset(result, 0, size);
#endif
	qcgc_hbtable_insert(result);
	result->flags = QCGC_GRAY_FLAG;

	qcgc_state.cells_since_incmark += bytes_to_cells(size);

	return result;
}

object_t *_qcgc_allocate_slowpath(size_t size) {
	bool use_fit_allocator = _qcgc_bump_allocator.ptr == NULL;
	size_t cells = bytes_to_cells(size);
#if LOG_ALLOCATOR_SWITCH
	bool old_use_fit_allocator = use_fit_allocator;
#endif

	if (UNLIKELY(qcgc_state.cells_since_incmark >
				qcgc_state.incmark_threshold)) {
		if (qcgc_state.incmark_since_sweep == qcgc_state.incmark_to_sweep) {
			qcgc_reset_bump_ptr();
			qcgc_collect();
			use_fit_allocator = false; // Try using bump allocator again
		} else {
			qcgc_incmark();
			qcgc_state.incmark_since_sweep++;
		}
	}

	object_t *result = NULL;
	if (!use_fit_allocator) {
		qcgc_bump_allocator_renew_block(size, false);

		qcgc_state.cells_since_incmark += _qcgc_bump_allocator.end -
			_qcgc_bump_allocator.ptr;

		cell_t *new_bump_ptr = _qcgc_bump_allocator.ptr + cells;
		if (_qcgc_bump_allocator.ptr != NULL &&
				new_bump_ptr <= _qcgc_bump_allocator.end) {
			// Bump allocate
			qcgc_arena_set_blocktype(qcgc_arena_addr(_qcgc_bump_allocator.ptr),
					qcgc_arena_cell_index(_qcgc_bump_allocator.ptr),
					BLOCK_WHITE);

			result = (object_t *) _qcgc_bump_allocator.ptr;
			_qcgc_bump_allocator.ptr = new_bump_ptr;

#if QCGC_INIT_ZERO
			memset(result, 0, cells * sizeof(cell_t));
#endif

			result->flags = QCGC_GRAY_FLAG;
#if LOG_ALLOCATOR_SWITCH
			if ((_qcgc_bump_allocator.ptr == NULL) != old_use_fit_allocator) {
				// Allocator switched
				struct log_info_s {
					size_t allocations;
					bool fit_allocator;
				};
				struct log_info_s log_info = {
					qcgc_allocations,
					_qcgc_bump_allocator.ptr == NULL,
				};
				qcgc_event_logger_log(EVENT_ALLOCATOR_SWITCH, sizeof(struct log_info_s),
						(uint8_t *) &log_info);
			}
#endif
			return result;
		}
	}

	// Fit allocate
	result = qcgc_fit_allocate(size);
	if (result != NULL) {
		qcgc_state.cells_since_incmark += bytes_to_cells(size);
#if LOG_ALLOCATOR_SWITCH
		if ((_qcgc_bump_allocator.ptr == NULL) != old_use_fit_allocator) {
			// Allocator switched
			struct log_info_s {
				size_t allocations;
				bool fit_allocator;
			};
			struct log_info_s log_info = {
				qcgc_allocations,
				_qcgc_bump_allocator.ptr == NULL,
			};
			qcgc_event_logger_log(EVENT_ALLOCATOR_SWITCH, sizeof(struct log_info_s),
					(uint8_t *) &log_info);
		}
#endif
		return result;
	}
	qcgc_bump_allocator_renew_block(size, true);
	qcgc_state.cells_since_incmark +=
		_qcgc_bump_allocator.end - _qcgc_bump_allocator.ptr;

	cell_t *new_bump_ptr = _qcgc_bump_allocator.ptr + cells;
	qcgc_arena_set_blocktype(qcgc_arena_addr(_qcgc_bump_allocator.ptr),
			qcgc_arena_cell_index(_qcgc_bump_allocator.ptr),
			BLOCK_WHITE);

	result = (object_t *) _qcgc_bump_allocator.ptr;
	_qcgc_bump_allocator.ptr = new_bump_ptr;

#if QCGC_INIT_ZERO
	memset(result, 0, cells * sizeof(cell_t));
#endif

	result->flags = QCGC_GRAY_FLAG;
#if LOG_ALLOCATOR_SWITCH
	if ((_qcgc_bump_allocator.ptr == NULL) != old_use_fit_allocator) {
		// Allocator switched
		struct log_info_s {
			size_t allocations;
			bool fit_allocator;
		};
		struct log_info_s log_info = {
			qcgc_allocations,
			_qcgc_bump_allocator.ptr == NULL,
		};
		qcgc_event_logger_log(EVENT_ALLOCATOR_SWITCH, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}
#endif
	return result;
}

/*
object_t *_qcgc_allocate_slowpath(size_t size) {
	object_t *result;

	if (UNLIKELY(qcgc_state.cells_since_incmark >
				qcgc_state.incmark_threshold)) {
		if (qcgc_state.incmark_since_sweep == qcgc_state.incmark_to_sweep) {
			qcgc_collect();
		} else {
			qcgc_incmark();
			qcgc_state.incmark_since_sweep++;
		}
	}

	// Use bump / fit allocator
	if (_qcgc_bump_allocator.ptr != NULL) {
		result = bump_allocate(size);
	} else {
		result = qcgc_fit_allocate(size);

		// Fallback to bump allocator
		if (result == NULL) {
			result = bump_allocate(size);
		}
	}
	return result;
}
*/

void qcgc_collect(void) {
	qcgc_mark();
	qcgc_sweep();
	qcgc_state.incmark_since_sweep = 0;
}

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
		qcgc_state.prebuilt_objects = qcgc_object_stack_push(
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
		qcgc_state.gray_stack_size++;
		qcgc_state.gp_gray_stack = qcgc_object_stack_push(
				qcgc_state.gp_gray_stack, object);
	} else if ((object_t *) qcgc_arena_addr((cell_t *) object) == object) {
		if (qcgc_hbtable_is_marked(object)) {
			// Push huge block to general purpose gray stack
			qcgc_state.gray_stack_size++;
			qcgc_state.gp_gray_stack = qcgc_object_stack_push(
					qcgc_state.gp_gray_stack, object);
		}
	} else {
		if (qcgc_arena_get_blocktype(qcgc_arena_addr((cell_t *) object),
					qcgc_arena_cell_index((cell_t *) object)) == BLOCK_BLACK) {
			// This was black before, push it to gray stack again
			arena_t *arena = qcgc_arena_addr((cell_t *) object);
			qcgc_state.gray_stack_size++;
			arena->gray_stack = qcgc_object_stack_push(
					arena->gray_stack, object);
		}
	}
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

QCGC_STATIC QCGC_INLINE void *_trap_page_addr(object_t **shadow_stack) {
	object_t **shadow_stack_end = shadow_stack + QCGC_SHADOWSTACK_SIZE;
	char *in_trap_page = (((char *)shadow_stack_end) + 4095);
	void *rounded_trap_page = (void *)(((uintptr_t)in_trap_page) & (~4095));
	return rounded_trap_page;
}

QCGC_STATIC QCGC_INLINE void initialize_shadowstack(void) {
	size_t stack_size = QCGC_SHADOWSTACK_SIZE * sizeof(object_t *);
	// allocate stack + size for alignement + trap page
	object_t **stack = (object_t **) malloc(stack_size + 8192);
	assert(stack != NULL);
	mprotect(_trap_page_addr(stack), 4096, PROT_NONE);

	_qcgc_shadowstack.top = stack;
	_qcgc_shadowstack.base = stack;
}

QCGC_STATIC void destroy_shadowstack(void) {
	mprotect(_trap_page_addr(_qcgc_shadowstack.base), 4096, PROT_READ |
				PROT_WRITE);

	free(_qcgc_shadowstack.base);
}
