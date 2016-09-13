#pragma once

#include "../qcgc.h"

#include <stdbool.h>

void qcgc_incmark(void);
void qcgc_mark(void);
void qcgc_sweep(void);
