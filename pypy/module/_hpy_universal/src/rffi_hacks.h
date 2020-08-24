#include "universal/hpy.h"

// work around rffi's lack of support for unions
typedef struct {
    HPyDef_Kind kind;
    HPySlot slot;
} _pypy_HPyDef_as_slot;

