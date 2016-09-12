#include "mark_list.h"

#include <assert.h>

#include <stdlib.h>
#include <string.h>

QCGC_STATIC mark_list_t *qcgc_mark_list_grow(mark_list_t *list);
QCGC_STATIC void qcgc_mark_list_check_invariant(mark_list_t *list);

mark_list_t *qcgc_mark_list_create(size_t initial_size) {
	size_t length = (initial_size + QCGC_MARK_LIST_SEGMENT_SIZE - 1) / QCGC_MARK_LIST_SEGMENT_SIZE;
	length += (size_t) length == 0;
	mark_list_t *result = (mark_list_t *)
		malloc(sizeof(mark_list_t) + length * sizeof(object_t **));
	result->head = 0;
	result->tail = 0;
	result->length = length;
	result->insert_index = 0;
	result->count = 0;
	result->segments[result->head] = (object_t **)
		calloc(QCGC_MARK_LIST_SEGMENT_SIZE, sizeof(object_t *));
#if CHECKED
	qcgc_mark_list_check_invariant(result);
#endif
	return result;
}

void qcgc_mark_list_destroy(mark_list_t *list) {
#if CHECKED
	qcgc_mark_list_check_invariant(list);
#endif

	size_t i = list->head;
	while (i != list->tail) {
		free(list->segments[i]);
		i = (i + 1) % list->length;
	}
	free(list->segments[list->tail]);
	free(list);
}

mark_list_t *qcgc_mark_list_push(mark_list_t *list, object_t *object) {
#if CHECKED
	assert(list != NULL);
	assert(object != NULL);

	qcgc_mark_list_check_invariant(list);
	size_t old_count = list->count;
#endif
	if (list->insert_index >= QCGC_MARK_LIST_SEGMENT_SIZE) {
		if ((list->tail + 1) % list->length == list->head) {
			list = qcgc_mark_list_grow(list);
		}
		list->insert_index = 0;
		list->tail = (list->tail + 1) % list->length;
		list->segments[list->tail] = (object_t **)
			calloc(QCGC_MARK_LIST_SEGMENT_SIZE, sizeof(object_t *));
	}
	list->segments[list->tail][list->insert_index] = object;
	list->insert_index++;
	list->count++;
#if CHECKED
	assert(list->count == old_count + 1);
	assert(list->segments[list->tail][list->insert_index - 1] == object);
	qcgc_mark_list_check_invariant(list);
#endif
	return list;
}

mark_list_t *qcgc_mark_list_push_all(mark_list_t *list,
		object_t **objects, size_t count) {
#if CHECKED
	assert(list != NULL);
	assert(objects != NULL);

	qcgc_mark_list_check_invariant(list);

	size_t old_count = list->count;
	for (size_t i = 0; i < count; i++) {
		assert(objects[i] != NULL);
	}
#endif
	// FIXME: Optimize or remove
	for (size_t i = 0; i < count; i++) {
		list = qcgc_mark_list_push(list, objects[i]);
	}
#if CHECKED
	assert(list->count == old_count + count);
	qcgc_mark_list_check_invariant(list);
#endif
	return list;
}

object_t **qcgc_mark_list_get_head_segment(mark_list_t *list) {
#if CHECKED
	assert(list != NULL);
	assert(list->segments[list->head] != NULL);
	qcgc_mark_list_check_invariant(list);
#endif
	return list->segments[list->head];
}

mark_list_t *qcgc_mark_list_drop_head_segment(mark_list_t *list) {
#if CHECKED
	assert(list != NULL);
	size_t old_head = list->head;
	size_t old_tail = list->tail;
	qcgc_mark_list_check_invariant(list);
#endif
	if (list->head != list->tail) {
		free(list->segments[list->head]);
		list->segments[list->head] = NULL;
		list->head = (list->head + 1) % list->length;
		list->count -= QCGC_MARK_LIST_SEGMENT_SIZE;
	} else {
		memset(list->segments[list->head], 0,
				sizeof(object_t *) * QCGC_MARK_LIST_SEGMENT_SIZE);
		list->insert_index = 0;
		list->count = 0;
	}
#if CHECKED
	assert(old_tail == list->tail);
	if (old_head == old_tail) {
		assert(old_head == list->head);
	} else {
		assert((old_head + 1) % list->length == list->head);
	}
	qcgc_mark_list_check_invariant(list);
#endif
	return list;
}

QCGC_STATIC mark_list_t *qcgc_mark_list_grow(mark_list_t *list) {
#if CHECKED
	assert(list != NULL);
	size_t old_length = list->length;
	size_t old_tail = list->tail;
	qcgc_mark_list_check_invariant(list);
#endif
	mark_list_t *new_list = (mark_list_t *) realloc(list,
			sizeof(mark_list_t) + 2 * list->length * sizeof(object_t **));
	if (new_list->tail < new_list->head) {
		memcpy(new_list->segments + new_list->length,
				new_list->segments, (new_list->tail + 1) * sizeof(object_t **));
		new_list->tail = new_list->length + new_list->tail;
	}
	new_list->length = 2 * new_list->length;
#if CHECKED
	assert(new_list->length == 2 * old_length);
	if (old_tail < new_list->head) {
		assert(new_list->tail == old_tail + old_length);
		for (size_t i = 0; i < old_tail; i++) {
			assert(new_list->segments[i] == new_list->segments[i + old_length]);
		}
	} else {
		assert(new_list->tail == old_tail);
	}
	qcgc_mark_list_check_invariant(new_list);
#endif
	return new_list;
}

QCGC_STATIC void qcgc_mark_list_check_invariant(mark_list_t *list) {
	assert(list->head < list->length);
	assert(list->tail < list->length);
	assert(list->count == (list->tail - list->head + list->length) % list->length * QCGC_MARK_LIST_SEGMENT_SIZE + list->insert_index);
	for (size_t i = 0; i < list->length; i++) {
		if ((list->head <= i && i <= list->tail) || (list->tail < list->head &&
				(i <= list->tail || i >= list->head))) {
			for (size_t j = 0; j < QCGC_MARK_LIST_SEGMENT_SIZE; j++) {
				if (i != list->tail || j < list->insert_index) {
					assert(list->segments[i][j] != NULL);
				} else {
					assert(list->segments[i][j] == NULL);
				}
			}
		}
	}
}
