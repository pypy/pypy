#include "src/precommondefs.h"

#ifdef RPYTHON_LL2CTYPES
/**************** BEFORE TRANSLATION ****************
 *
 * Define a set of macros to turn a call to foo() into bridge->foo()
 *
 */

#define hpy_err_occurred_rpy() (hpy_get_bridge()->hpy_err_occurred_rpy())

typedef struct {
    int (*hpy_err_occurred_rpy)(void);
} _HPyBridge;


RPY_EXTERN _HPyBridge *hpy_get_bridge(void);

#else /* RPYTHON_LL2CTYPES */
/**************** AFTER TRANSLATION ****************
 *
 * Declare standard function prototypes
 *
 */

int hpy_err_occurred_rpy(void);

#endif /* RPYTHON_LL2CTYPES */
