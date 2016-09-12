#pragma once

#include "config.h"

#include <stdbool.h>

#include "object.h"

QCGC_STATIC void qcgc_mark(bool incremental);
QCGC_STATIC void qcgc_sweep(void);

extern void qcgc_trace_cb(object_t *object, void (*visit)(object_t *object));
