#include "src/precommondefs.h"
#include "universal/hpy.h"

/* One note about bridge functions which receive arguments of type HPy: in C,
 * HPy is defined as:
 *     typedef struct { HPy_ssize_t _i; } HPy;
 *
 * however, as explained in llapi.py, to work around limitations of
 * rffi/ll2ctypes, on the RPython side HPy is defined as:
 *     typedef HPy_ssize_t HPy;
 *
 * This poses a problem for bridge functions, because the types don't
 * match. The workaround is to use a macro to convert from HPy to HPy_ssize_t
 * by doing h._i.  The naming convention is that in RPython we define a
 * @BRIGE.func called _foo, and here we define a macro foo which calls
 * _foo(h._i)
 *
 */

#ifdef RPYTHON_LL2CTYPES
/**************** BEFORE TRANSLATION ****************
 *
 * Define a set of macros to turn a call to foo() into bridge->foo()
 *
 */

#define hpy_err_Occurred_rpy() (hpy_get_bridge()->hpy_err_Occurred_rpy())
#define hpy_err_SetString(a, b, c) (hpy_get_bridge()->_hpy_err_SetString(a, b, c))

typedef struct {
    int (*hpy_err_Occurred_rpy)(void);
    void (*_hpy_err_SetString)(HPyContext ctx, HPy type, const char* message);
} _HPyBridge;


RPY_EXTERN _HPyBridge *hpy_get_bridge(void);

#else /* RPYTHON_LL2CTYPES */
/**************** AFTER TRANSLATION ****************
 *
 * Declare standard function prototypes
 *
 */

// see the comment above for why we need this macro
#define hpy_err_SetString(ctx, type, message) (_hpy_err_SetString(ctx, type._i, message))

int hpy_err_Occurred_rpy(void);
void _hpy_err_SetString(HPyContext ctx, HPy_ssize_t type, const char *message);

#endif /* RPYTHON_LL2CTYPES */
