#include "shadow_stack.h"

#include <assert.h>
#include <stdlib.h>

QCGC_STATIC size_t shadow_stack_size(size_t size);
QCGC_STATIC shadow_stack_t *shadow_stack_grow(shadow_stack_t *stack);
QCGC_STATIC shadow_stack_t *shadow_stack_shrink(shadow_stack_t *stack);

shadow_stack_t *qcgc_shadow_stack_create(size_t size) {
	shadow_stack_t *result = (shadow_stack_t *) malloc(shadow_stack_size(size));
	result->size = size;
	result->count = 0;
	return result;
}

shadow_stack_t *qcgc_shadow_stack_push(shadow_stack_t *stack, object_t *item) {
	if (stack->size == stack->count) {
		stack = shadow_stack_grow(stack);
	}
	stack->items[stack->count] = item;
	stack->count++;
	return stack;
}

object_t *qcgc_shadow_stack_top(shadow_stack_t *stack) {
#if CHECKED
	assert(stack->count != 0);
#endif
	return stack->items[stack->count - 1];
}

shadow_stack_t *qcgc_shadow_stack_pop(shadow_stack_t *stack) {
	// TODO: Add lower bound for size (config.h)
	if (stack->count < stack->size / 4) {
		stack = shadow_stack_shrink(stack);
	}
	stack->count--;
	return stack;
}

QCGC_STATIC size_t shadow_stack_size(size_t size) {
	return (sizeof(shadow_stack_t) + size * sizeof(object_t *));
}

QCGC_STATIC shadow_stack_t *shadow_stack_grow(shadow_stack_t *stack) {
	stack = (shadow_stack_t *) realloc(stack, shadow_stack_size(stack->size * 2));
	stack->size *= 2;
	return stack;
}

QCGC_STATIC shadow_stack_t *shadow_stack_shrink(shadow_stack_t *stack) {
	stack = (shadow_stack_t *) realloc(stack, shadow_stack_size(stack->size / 2));
	stack->size /= 2;
	return stack;
}
