#pragma once

#include "config.h"

#include <stddef.h>

#include "object.h"


void qcgc_initialize(void);
void qcgc_destroy(void);
object_t *qcgc_allocate(size_t size);
void qcgc_collect(void);
void qcgc_write(object_t *object);
