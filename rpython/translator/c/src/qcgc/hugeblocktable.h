#pragma once

#include "config.h"

#include <stdbool.h>

#include "bag.h"
#include "object.h"
#include "gray_stack.h"

// Choosing a prime number, hoping for good results
#define QCGC_HBTABLE_BUCKETS 61

struct hbtable_s {
	bool mark_flag_ref;
	hbbucket_t *bucket[QCGC_HBTABLE_BUCKETS];
} qcgc_hbtable;

void qcgc_hbtable_initialize(void);
void qcgc_hbtable_destroy(void);
void qcgc_hbtable_insert(object_t *object);
bool qcgc_hbtable_mark(object_t *object);
bool qcgc_hbtable_is_marked(object_t *object);
void qcgc_hbtable_sweep(void);
