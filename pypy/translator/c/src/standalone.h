
#include <stdlib.h>
#include <limits.h>
#include <assert.h>
#include <math.h>

#ifndef PYPY_NOT_MAIN_FILE
#ifndef WITH_PYMALLOC
#define WITH_PYMALLOC
#endif
#include "obmalloc.c"
#endif
