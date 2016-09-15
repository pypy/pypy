#include "object_stack.h"

#include <stdlib.h>

QCGC_STATIC QCGC_INLINE size_t object_stack_size(size_t size);

object_stack_t *qcgc_object_stack_create(size_t size) {
	object_stack_t *result = (object_stack_t *) malloc(object_stack_size(size));
	result->size = size;
	result->count = 0;
	return result;
}

QCGC_STATIC size_t object_stack_size(size_t size) {
	return (sizeof(object_stack_t) + size * sizeof(object_t *));
}

object_stack_t *object_stack_grow(object_stack_t *stack) {
	stack = (object_stack_t *) realloc(stack,
			object_stack_size(stack->size * 2));
	stack->size *= 2;
	return stack;
}

object_stack_t *object_stack_shrink(object_stack_t *stack) {
	stack = (object_stack_t *) realloc(stack,
			object_stack_size(stack->size / 2));
	stack->size /= 2;
	return stack;
}
