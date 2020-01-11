#include <stdarg.h>
#include "universal/hpy.h"
#include "src/precommondefs.h"

RPY_EXTERN int ctx_Arg_Parse(HPyContext ctx, HPy *args, HPy_ssize_t nargs,
                             const char *fmt, va_list vl);
