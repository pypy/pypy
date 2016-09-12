#pragma once

#include "config.h"

#include "object.h"

void qcgc_register_weakref(object_t *weakrefobj, object_t **target);
QCGC_STATIC void update_weakrefs(void);
