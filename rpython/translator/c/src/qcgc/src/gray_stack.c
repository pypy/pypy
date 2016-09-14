#include "gray_stack.h"

#include <stdlib.h>

QCGC_STATIC size_t gray_stack_size(size_t size);

gray_stack_t *qcgc_gray_stack_create(size_t size) {
	gray_stack_t *result = (gray_stack_t *) malloc(gray_stack_size(size));
	result->size = size;
	result->index = 0;
	return result;
}

QCGC_STATIC size_t gray_stack_size(size_t size) {
	return (sizeof(gray_stack_t) + size * sizeof(object_t *));
}

gray_stack_t *gray_stack_grow(gray_stack_t *stack) {
	stack = (gray_stack_t *) realloc(stack, gray_stack_size(stack->size * 2));
	stack->size *= 2;
	return stack;
}

gray_stack_t *gray_stack_shrink(gray_stack_t *stack) {
	stack = (gray_stack_t *) realloc(stack, gray_stack_size(stack->size / 2));
	stack->size /= 2;
	return stack;
}
