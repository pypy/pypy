#include "collector.h"

#include "arena.h"
#include "allocator.h"
#include "gc_state.h"
#include "event_logger.h"
#include "hugeblocktable.h"
#include "weakref.h"

QCGC_STATIC QCGC_INLINE void qcgc_pop_object(object_t *object);
QCGC_STATIC QCGC_INLINE void qcgc_push_object(object_t *object);
QCGC_STATIC void mark_setup(bool incremental);
QCGC_STATIC void mark_cleanup(bool incremental);

QCGC_STATIC void check_free_cells(void);
QCGC_STATIC void check_largest_free_block(void);

void qcgc_mark(void) {
	mark_setup(false);

	while (qcgc_state.gray_stack_size > 0) {
		// General purpose gray stack (prebuilt objects and huge blocks)

		while (qcgc_state.gp_gray_stack->count > 0) {
			object_t *top = qcgc_object_stack_top(qcgc_state.gp_gray_stack);
			qcgc_state.gray_stack_size--;
			qcgc_state.gp_gray_stack = qcgc_object_stack_pop(
					qcgc_state.gp_gray_stack);
			qcgc_pop_object(top);
		}

		// Arena gray stacks
		for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
			arena_t *arena = qcgc_allocator_state.arenas->items[i];

			while (arena->gray_stack->count > 0) {
				object_t *top = qcgc_object_stack_top(arena->gray_stack);
				qcgc_state.gray_stack_size--;
				arena->gray_stack = qcgc_object_stack_pop(arena->gray_stack);
				qcgc_pop_object(top);
			}
		}
	}

	mark_cleanup(false);

#if CHECKED
	assert(qcgc_state.phase == GC_COLLECT);
#endif
}

void qcgc_incmark(void) {
	mark_setup(true);

	// General purpose gray stack (prebuilt objects and huge blocks)
	size_t to_process = MAX(qcgc_state.gp_gray_stack->count / 2,
			QCGC_INC_MARK_MIN);

	while (to_process > 0 && qcgc_state.gp_gray_stack->count > 0) {
		object_t *top = qcgc_object_stack_top(qcgc_state.gp_gray_stack);
		qcgc_state.gray_stack_size--;
		qcgc_state.gp_gray_stack = qcgc_object_stack_pop(
				qcgc_state.gp_gray_stack);
		qcgc_pop_object(top);
		to_process--;
	}

	// Arena gray stacks
	for (size_t i = 0; i < qcgc_allocator_state.arenas->count; i++) {
		arena_t *arena = qcgc_allocator_state.arenas->items[i];
		to_process = MAX(arena->gray_stack->count / 2, QCGC_INC_MARK_MIN);

		while (to_process > 0 && arena->gray_stack->count > 0) {
			object_t *top = qcgc_object_stack_top(arena->gray_stack);
			qcgc_state.gray_stack_size--;
			arena->gray_stack = qcgc_object_stack_pop(arena->gray_stack);
			qcgc_pop_object(top);
			to_process--;
		}
	}


	mark_cleanup(true);
#if CHECKED
	assert(qcgc_state.phase != GC_PAUSE);
#endif
}

QCGC_STATIC void mark_setup(bool incremental) {
	{
		struct log_info_s {
			bool incremental;
			size_t gray_stack_size;
		};
		struct log_info_s log_info = {incremental, qcgc_state.gray_stack_size};
		qcgc_event_logger_log(EVENT_MARK_START, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}

	qcgc_state.cells_since_incmark = 0;

	if (qcgc_state.phase == GC_PAUSE) {

		// If we do this for the first time, push all prebuilt objects.
		// All further changes to prebuilt objects will go to the gp_gray_stack
		// because of the write barrier
		size_t count = qcgc_state.prebuilt_objects->count;
		for (size_t i = 0; i < count; i++) {
			qcgc_state.gray_stack_size++;
			qcgc_state.gp_gray_stack = qcgc_object_stack_push(
					qcgc_state.gp_gray_stack,
					qcgc_state.prebuilt_objects->items[i]);
		}
	}

	qcgc_state.phase = GC_MARK;

	// Always push all roots to make shadowstack pushes faster
	for (object_t **it = _qcgc_shadowstack.base;
		it < _qcgc_shadowstack.top;
		it++) {
		qcgc_push_object(*it);
	}

}

QCGC_STATIC void mark_cleanup(bool incremental) {
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
}

QCGC_STATIC QCGC_INLINE void qcgc_pop_object(object_t *object) {
#if CHECKED
	assert(object != NULL);
	assert((object->flags & QCGC_PREBUILT_OBJECT) == QCGC_PREBUILT_OBJECT ||
			(object->flags & QCGC_GRAY_FLAG) == QCGC_GRAY_FLAG);
	if (((object->flags & QCGC_PREBUILT_OBJECT) == 0) &&
		((object_t *) qcgc_arena_addr((cell_t *) object) != object)) {
		assert(qcgc_arena_get_blocktype(qcgc_arena_addr((cell_t *) object),
					qcgc_arena_cell_index((cell_t *) object)) == BLOCK_BLACK);
	}
#endif
	object->flags &= ~QCGC_GRAY_FLAG;
	qcgc_trace_cb(object, &qcgc_push_object);
}

QCGC_STATIC QCGC_INLINE void qcgc_push_object(object_t *object) {
#if CHECKED
	assert(qcgc_state.phase == GC_MARK);
#endif
	if (object != NULL) {
		arena_t *arena = qcgc_arena_addr((cell_t *) object);
		if ((object_t *) arena == object) {
			if (qcgc_hbtable_mark(object)) {
				// Did mark it / was white before
				object->flags |= QCGC_GRAY_FLAG;
				qcgc_state.gray_stack_size++;
				qcgc_state.gp_gray_stack = qcgc_object_stack_push(
						qcgc_state.gp_gray_stack, object);
			}
			return;
		}
		if ((object->flags & QCGC_PREBUILT_OBJECT) != 0) {
			return;
		}
		size_t index = qcgc_arena_cell_index((cell_t *) object);
		if (qcgc_arena_get_blocktype(arena, index) == BLOCK_WHITE) {
			object->flags |= QCGC_GRAY_FLAG;
			qcgc_arena_set_blocktype(arena, index, BLOCK_BLACK);
			qcgc_state.gray_stack_size++;
			arena->gray_stack = qcgc_object_stack_push(arena->gray_stack, object);
		}
	}
}

void qcgc_sweep(void) {
#if CHECKED
	assert(qcgc_state.phase == GC_COLLECT);
	check_free_cells();
#endif
	{
		struct log_info_s {
			size_t arenas;
			size_t free_cells;
		};
		struct log_info_s log_info = {
			qcgc_allocator_state.arenas->count,
			qcgc_state.free_cells,
		};
		qcgc_event_logger_log(EVENT_SWEEP_START, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
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
#if CHECKED
	check_free_cells();
	check_largest_free_block();
#endif
	update_weakrefs();

	{
		struct log_info_s {
			size_t arenas;
			size_t free_cells;
			size_t largest_free_block;
		};
		struct log_info_s log_info = {
			qcgc_allocator_state.arenas->count,
			qcgc_state.free_cells,
			qcgc_state.largest_free_block
		};
		qcgc_event_logger_log(EVENT_SWEEP_DONE, sizeof(struct log_info_s),
				(uint8_t *) &log_info);
	}
#if LOG_DUMP_FREELIST_STATS
	{
		struct log_info_s {
			size_t class;
			size_t items;
		};
		struct log_info_s log_info;

		for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
			log_info = (struct log_info_s){ i + 1,
				qcgc_allocator_state.fit_state.small_free_list[i]->count};
			qcgc_event_logger_log(EVENT_FREELIST_DUMP,
					sizeof(struct log_info_s), (uint8_t *) &log_info);
		}
		for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
			log_info = (struct log_info_s){
				1<<(QCGC_LARGE_FREE_LIST_FIRST_EXP + i),
				qcgc_allocator_state.fit_state.large_free_list[i]->count};
			qcgc_event_logger_log(EVENT_FREELIST_DUMP,
					sizeof(struct log_info_s), (uint8_t *) &log_info);
		}
	}
#endif
}

void check_free_cells(void) {
	size_t free_cells = 0;
		for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
			free_cells += qcgc_allocator_state.fit_state.small_free_list[i]
				->count * (i + 1);
		}
		for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
			for (size_t j = 0; j < qcgc_allocator_state.fit_state.
					large_free_list[i]->count; j++) {
				free_cells += qcgc_allocator_state.fit_state.large_free_list[i]
					->items[j].size;
			}
		}
	assert(free_cells == qcgc_state.free_cells);
	assert(free_cells <= qcgc_allocator_state.arenas->count * (QCGC_ARENA_CELLS_COUNT - QCGC_ARENA_FIRST_CELL_INDEX));
	assert(qcgc_allocator_state.arenas->count *
			(QCGC_ARENA_CELLS_COUNT - QCGC_ARENA_FIRST_CELL_INDEX) >=
			free_cells);
}

void check_largest_free_block(void) {
	size_t largest_free_block = 0;
		for (size_t i = 0; i < QCGC_SMALL_FREE_LISTS; i++) {
			if (qcgc_allocator_state.fit_state.small_free_list[i]->count > 0) {
				largest_free_block = i + 1;
			}
		}
		for (size_t i = 0; i < QCGC_LARGE_FREE_LISTS; i++) {
			for (size_t j = 0; j < qcgc_allocator_state.fit_state.
					large_free_list[i]->count; j++) {
				largest_free_block = MAX(largest_free_block,
					qcgc_allocator_state.fit_state.large_free_list[i]
					->items[j].size);
			}
		}
	assert(largest_free_block == qcgc_state.largest_free_block);
}
