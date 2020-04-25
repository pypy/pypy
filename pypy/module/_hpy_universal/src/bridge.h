#include "src/precommondefs.h"
#include "universal/hpy.h"

#ifdef RPYTHON_LL2CTYPES
/**************** BEFORE TRANSLATION ****************
 *
 * Define a set of macros to turn a call to foo() into bridge->foo()
 *
 */

#define hpy_err_Occurred_rpy() (hpy_get_bridge()->hpy_err_Occurred_rpy())
#define hpy_err_SetString(a, b, c) (hpy_get_bridge()->hpy_err_SetString(a, b, c))

typedef struct {
    int (*hpy_err_Occurred_rpy)(void);
    void (*hpy_err_SetString)(HPyContext ctx, HPy type, const char* message);
} _HPyBridge;


RPY_EXTERN _HPyBridge *hpy_get_bridge(void);

#else /* RPYTHON_LL2CTYPES */
/**************** AFTER TRANSLATION ****************
 *
 * Declare standard function prototypes
 *
 */

int hpy_err_Occurred_rpy(void);
void hpy_err_SetString(HPyContext ctx, HPy type, const char *message);

#endif /* RPYTHON_LL2CTYPES */
