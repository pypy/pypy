#include "src/precommondefs.h"
#include "universal/hpy.h"

RPY_EXTERN int pypy_HPyErr_Occurred(HPyContext ctx);
RPY_EXTERN void pypy_HPyErr_SetString(HPyContext ctx, HPy type, const char *message);
RPY_EXTERN void pypy_HPyErr_Clear(HPyContext ctx);
