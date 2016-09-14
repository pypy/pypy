#pragma once

#include "../qcgc.h"

typedef struct gray_stack_s {
	size_t index;
	size_t size;
	object_t *items[];
} gray_stack_t;

__attribute__ ((warn_unused_result))
gray_stack_t *qcgc_gray_stack_create(size_t size);

__attribute__ ((warn_unused_result))
gray_stack_t *gray_stack_grow(gray_stack_t *stack);

__attribute__ ((warn_unused_result))
gray_stack_t *gray_stack_shrink(gray_stack_t *stack);

__attribute__ ((warn_unused_result))
QCGC_STATIC QCGC_INLINE gray_stack_t *qcgc_gray_stack_push(
		gray_stack_t *stack, object_t *item) {
	if (stack->size == stack->index) {
		stack = gray_stack_grow(stack);
	}
	stack->items[stack->index] = item;
	stack->index++;
	return stack;
}

QCGC_STATIC QCGC_INLINE object_t *qcgc_gray_stack_top(gray_stack_t *stack) {
#if CHECKED
	assert(stack->index != 0);
#endif
	return stack->items[stack->index - 1];
}

__attribute__ ((warn_unused_result))
QCGC_STATIC QCGC_INLINE gray_stack_t *qcgc_gray_stack_pop(gray_stack_t *stack) {
	// TODO: Add lower bound for size (config.h)
	if (stack->index < stack->size / 4) {
		stack = gray_stack_shrink(stack);
	}
	stack->index--;
	return stack;
}
