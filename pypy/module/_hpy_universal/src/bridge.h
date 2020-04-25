#include "src/precommondefs.h"

#ifdef RPYTHON_LL2CTYPES
/**************** BEFORE TRANSLATION ****************
 *
 * Define a set of macros to turn a call to foo() into bridge->foo()
 *
 */

#define _HPyErr_Occurred_rpy() (hpy_get_bridge()->_HPyErr_Occurred_rpy())

typedef struct {
    int (*_HPyErr_Occurred_rpy)(void);
} _HPyBridge;


RPY_EXTERN _HPyBridge *hpy_get_bridge(void);

#else /* RPYTHON_LL2CTYPES */
/**************** AFTER TRANSLATION ****************
 *
 * Declare standard function prototypes
 *
 */

int _HPyErr_Occurred_rpy(void);

#endif /* RPYTHON_LL2CTYPES */
