#pragma once

#include "config.h"

#include <stddef.h>

#include "object.h"

typedef struct gray_stack_s {
	size_t index;
	size_t size;
	object_t *items[];
} gray_stack_t;

gray_stack_t *qcgc_gray_stack_create(size_t size);

gray_stack_t *qcgc_gray_stack_push(gray_stack_t *stack, object_t *item);
object_t *qcgc_gray_stack_top(gray_stack_t *stack);
gray_stack_t *qcgc_gray_stack_pop(gray_stack_t *stack);
