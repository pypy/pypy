#include "gray_stack.h"

#include <assert.h>
#include <stdlib.h>

#include "gc_state.h"

QCGC_STATIC size_t gray_stack_size(size_t size);
QCGC_STATIC gray_stack_t *gray_stack_grow(gray_stack_t *stack);
QCGC_STATIC gray_stack_t *gray_stack_shrink(gray_stack_t *stack);

gray_stack_t *qcgc_gray_stack_create(size_t size) {
	gray_stack_t *result = (gray_stack_t *) malloc(gray_stack_size(size));
	result->size = size;
	result->index = 0;
	return result;
}

gray_stack_t *qcgc_gray_stack_push(gray_stack_t *stack, object_t *item) {
	if (stack->size == stack->index) {
		stack = gray_stack_grow(stack);
	}
	stack->items[stack->index] = item;
	stack->index++;
	qcgc_state.gray_stack_size++;
	return stack;
}

object_t *qcgc_gray_stack_top(gray_stack_t *stack) {
#if CHECKED
	assert(stack->index != 0);
#endif
	return stack->items[stack->index - 1];
}

gray_stack_t *qcgc_gray_stack_pop(gray_stack_t *stack) {
	// TODO: Add lower bound for size (config.h)
	if (stack->index < stack->size / 4) {
		stack = gray_stack_shrink(stack);
	}
	stack->index--;
	qcgc_state.gray_stack_size--;
	return stack;
}

QCGC_STATIC size_t gray_stack_size(size_t size) {
	return (sizeof(gray_stack_t) + size * sizeof(object_t *));
}

QCGC_STATIC gray_stack_t *gray_stack_grow(gray_stack_t *stack) {
	stack = (gray_stack_t *) realloc(stack, gray_stack_size(stack->size * 2));
	stack->size *= 2;
	return stack;
}

QCGC_STATIC gray_stack_t *gray_stack_shrink(gray_stack_t *stack) {
	stack = (gray_stack_t *) realloc(stack, gray_stack_size(stack->size / 2));
	stack->size /= 2;
	return stack;
}
