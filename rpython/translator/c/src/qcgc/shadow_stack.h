#pragma once

#include "config.h"

#include <stddef.h>

#include "object.h"

typedef struct shadow_stack_s {
	size_t count;
	size_t size;
	object_t *items[];
} shadow_stack_t;

shadow_stack_t *qcgc_shadow_stack_create(size_t size);

shadow_stack_t *qcgc_shadow_stack_push(shadow_stack_t *stack, object_t *item);
object_t *qcgc_shadow_stack_top(shadow_stack_t *stack);
shadow_stack_t *qcgc_shadow_stack_pop(shadow_stack_t *stack);
