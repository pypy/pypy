#include "hugeblocktable.h"

#include <assert.h>

QCGC_STATIC size_t bucket(object_t *object);

void qcgc_hbtable_initialize(void) {
	qcgc_hbtable.mark_flag_ref = false;
	for (size_t i = 0; i < QCGC_HBTABLE_BUCKETS; i++) {
		qcgc_hbtable.bucket[i] = qcgc_hbbucket_create(4);
	}
}

void qcgc_hbtable_destroy(void) {
	for (size_t i = 0; i < QCGC_HBTABLE_BUCKETS; i++) {
		free(qcgc_hbtable.bucket[i]);
	}
}

void qcgc_hbtable_insert(object_t *object) {
	size_t i = bucket(object);
	qcgc_hbtable.bucket[i] = qcgc_hbbucket_add(qcgc_hbtable.bucket[i],
			(struct hbtable_entry_s) {
				.object = object,
				.mark_flag = !qcgc_hbtable.mark_flag_ref});
}

bool qcgc_hbtable_mark(object_t *object) {
	hbbucket_t *b = qcgc_hbtable.bucket[bucket(object)];
	size_t count = b->count;
	for (size_t i = 0; i < count; i++) {
		if (b->items[i].object == object) {
			if (b->items[i].mark_flag != qcgc_hbtable.mark_flag_ref) {
				b->items[i].mark_flag = qcgc_hbtable.mark_flag_ref;
				return true;
			}
			return false;
		}
	}
#if CHECKED
	assert(false);
#endif
	return false;
}

bool qcgc_hbtable_has(object_t *object) {
	hbbucket_t *b = qcgc_hbtable.bucket[bucket(object)];
	size_t count = b->count;
	for (size_t i = 0; i < count; i++) {
		if (b->items[i].object == object) {
			return true;
		}
	}
	return false;
}

bool qcgc_hbtable_is_marked(object_t *object) {
	hbbucket_t *b = qcgc_hbtable.bucket[bucket(object)];
	size_t count = b->count;
	for (size_t i = 0; i < count; i++) {
		if (b->items[i].object == object) {
			return b->items[i].mark_flag == qcgc_hbtable.mark_flag_ref;
		}
	}
	return false;
}

void qcgc_hbtable_sweep(void) {
	for (size_t i = 0; i < QCGC_HBTABLE_BUCKETS; i++) {
		hbbucket_t *b = qcgc_hbtable.bucket[i];
		size_t j = 0;
		while(j < b->count) {
			if (b->items[j].mark_flag != qcgc_hbtable.mark_flag_ref) {
				// White object
				free(b->items[j].object);
				b = qcgc_hbbucket_remove_index(b, j);
			} else {
				// Black object
				j++;
			}
		}
		qcgc_hbtable.bucket[i] = b;
	}
	qcgc_hbtable.mark_flag_ref = !qcgc_hbtable.mark_flag_ref;
}

QCGC_STATIC size_t bucket(object_t *object) {
	return ((uintptr_t) object >> (QCGC_ARENA_SIZE_EXP)) % QCGC_HBTABLE_BUCKETS;
}
