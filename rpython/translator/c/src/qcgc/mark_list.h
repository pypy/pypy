/**
 * @file	mark_list.h
 *
 * Object list for marking step
 */

#pragma once

#include "config.h"

#include <stddef.h>

#include "object.h"

/**
 * Mark list - circular buffer.
 */
typedef struct mark_list_s {
	size_t head;
	size_t tail;
	size_t length;
	size_t count;
	size_t insert_index;
	object_t **segments[];
} mark_list_t;

mark_list_t *qcgc_mark_list_create(size_t initial_size);
void qcgc_mark_list_destroy(mark_list_t *list);

mark_list_t *qcgc_mark_list_push(mark_list_t *list, object_t *object);
mark_list_t *qcgc_mark_list_push_all(mark_list_t *list,
		object_t **objects, size_t count);

object_t **qcgc_mark_list_get_head_segment(mark_list_t *list);
mark_list_t *qcgc_mark_list_drop_head_segment(mark_list_t *list);
