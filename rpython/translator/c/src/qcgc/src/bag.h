#pragma once

#include "../qcgc.h"

#include <stdlib.h>

#include "arena.h"

#define DECLARE_BAG(name, type)												\
typedef struct name##_s {													\
	size_t size;															\
	size_t count;															\
	type items[];															\
} name##_t;																	\
																			\
__attribute__ ((warn_unused_result))										\
name##_t *qcgc_##name##_create(size_t size);								\
																			\
__attribute__ ((warn_unused_result))										\
name##_t *qcgc_##name##_add(name##_t *self, type item);						\
																			\
__attribute__ ((warn_unused_result))										\
name##_t *qcgc_##name##_remove_index(name##_t *self, size_t index);

#define DEFINE_BAG(name, type)												\
																			\
QCGC_STATIC size_t name##_size(size_t size);								\
																			\
__attribute__ ((warn_unused_result))										\
QCGC_STATIC name##_t *name##_grow(name##_t *self);							\
																			\
__attribute__ ((warn_unused_result))										\
QCGC_STATIC name##_t *name##_shrink(name##_t *self);						\
																			\
name##_t *qcgc_##name##_create(size_t size) {								\
	name##_t *result = (name##_t *) malloc(name##_size(size));				\
	result->size = size;													\
	result->count = 0;														\
	return result;															\
}																			\
																			\
name##_t *qcgc_##name##_add(name##_t *self, type item) {					\
	if (self->count >= self->size) {										\
		self = name##_grow(self);											\
	}																		\
	self->items[self->count++] = item;										\
	return self;															\
}																			\
																			\
name##_t *qcgc_##name##_remove_index(name##_t *self, size_t index) {		\
	if (index + 1 < self->count) {											\
		self->items[index] = self->items[self->count - 1];					\
	}																		\
	self->count--;															\
																			\
	if (self->count < self->size / 4) {										\
		self = name##_shrink(self);											\
	}																		\
	return self;															\
}																			\
																			\
QCGC_STATIC name##_t *name##_grow(name##_t *self) {								\
	name##_t *new_self = (name##_t *) realloc(self,							\
			name##_size(self->size * 2));									\
	assert(new_self != NULL);												\
	self = new_self;														\
	self->size *= 2;														\
	return self;															\
}																			\
																			\
QCGC_STATIC name##_t *name##_shrink(name##_t *self) {							\
	name##_t *new_self = (name##_t *) realloc(self,							\
			name##_size(self->size / 2));									\
	assert(new_self != NULL);												\
	self = new_self;														\
	self->size /= 2;														\
	return self;															\
}																			\
																			\
QCGC_STATIC size_t name##_size(size_t size) {									\
	return sizeof(name##_t) + size * sizeof(type);							\
}

struct exp_free_list_item_s {
	cell_t *ptr;
	size_t size;
};

struct hbtable_entry_s {
	object_t *object;
	bool mark_flag;
};

struct weakref_bag_item_s {
	object_t *weakrefobj;
	object_t **target;
};

DECLARE_BAG(arena_bag, arena_t *);
DECLARE_BAG(linear_free_list, cell_t *);
DECLARE_BAG(exp_free_list, struct exp_free_list_item_s);
DECLARE_BAG(hbbucket, struct hbtable_entry_s);
DECLARE_BAG(weakref_bag, struct weakref_bag_item_s);
