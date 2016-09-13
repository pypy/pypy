#pragma once

#include "../qcgc.h"

#include <stdbool.h>

void qcgc_mark(bool incremental);
void qcgc_sweep(void);
