#pragma once

#include "../qcgc.h"

__attribute__ ((warn_unused_result))
object_stack_t *qcgc_object_stack_create(size_t size);

__attribute__ ((warn_unused_result))
object_stack_t *object_stack_grow(object_stack_t *stack);

__attribute__ ((warn_unused_result))
object_stack_t *object_stack_shrink(object_stack_t *stack);

__attribute__ ((warn_unused_result))
QCGC_STATIC QCGC_INLINE object_stack_t *qcgc_object_stack_push(
		object_stack_t *stack, object_t *item) {
	if (stack->size == stack->count) {
		stack = object_stack_grow(stack);
	}
	stack->items[stack->count] = item;
	stack->count++;
	return stack;
}

QCGC_STATIC QCGC_INLINE object_t *qcgc_object_stack_top(object_stack_t *stack) {
#if CHECKED
	assert(stack->count != 0);
#endif
	return stack->items[stack->count - 1];
}

__attribute__ ((warn_unused_result))
QCGC_STATIC QCGC_INLINE object_stack_t *qcgc_object_stack_pop(
		object_stack_t *stack) {
	// TODO: Add lower bound for size (config.h)
	if (stack->count < stack->size / 4) {
		stack = object_stack_shrink(stack);
	}
	stack->count--;
	return stack;
}
