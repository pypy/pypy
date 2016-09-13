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
gray_stack_t *qcgc_gray_stack_push(gray_stack_t *stack, object_t *item);

object_t *qcgc_gray_stack_top(gray_stack_t *stack);

__attribute__ ((warn_unused_result))
gray_stack_t *qcgc_gray_stack_pop(gray_stack_t *stack);
