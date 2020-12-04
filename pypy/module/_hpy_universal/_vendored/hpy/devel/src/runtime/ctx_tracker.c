/**
 * A manager for HPy handles, allowing handles to be tracked
 * and closed as a group.
 *
 * Note::
 *    Calling HPyTracker_New(ctx, n) will ensure that at least n handles
 *    can be tracked without a call to HPyTracker_Add failing.
 *
 *    If a call to HPyTracker_Add fails, the tracker still guarantees that
 *    the handle passed to it has been tracked (internally it does this by
 *    maintaining space for one more handle).
 *
 *    After HPyTracker_Add fails, HPyTracker_Close should be called without
 *    any further calls to HPyTracker_Add. Calling HPyTracker_Close will close
 *    all the tracked handles, including the handled passed to the failed call
 *    to HPyTracker_Add.
 *
 * Example usage (inside an HPyDef_METH function)::
 *
 * long i;
 * HPy key, value;
 * HPyTracker ht;
 *
 * ht = HPyTracker_New(ctx, 0);  // track the key-value pairs
 * if (HPy_IsNull(ht))
 *     return HPy_NULL;
 *
 * HPy dict = HPyDict_New(ctx);
 * if (HPy_IsNull(dict))
 *     goto error;
 *
 * for (i=0; i<5; i++) {
 *     key = HPyLong_FromLong(ctx, i);
 *     if (HPy_IsNull(key))
 *         goto error;
 *     if (HPyTracker_Add(ctx, ht, key) < 0)
 *         goto error;
 *     value = HPyLong_FromLong(ctx, i * i);
 *     if (HPy_IsNull(value)) {
 *         goto error;
 *     }
 *     if (HPyTracker_Add(ctx, ht, value) < 0)
 *         goto error;
 *     result = HPy_SetItem(ctx, dict, key, value);
 *     if (result < 0)
 *         goto error;
 * }
 *
 * success:
 *    HPyTracker_Close(ctx, ht);
 *    return dict;
 *
 * error:
 *    HPyTracker_Close(ctx, ht);
 *    HPy_Close(ctx, dict);
 *    // HPyErr will already have been set by the error that occurred.
 *    return HPy_NULL;
 */

#include <Python.h>
#include "hpy.h"
#include "common/runtime/ctx_type.h"

#ifdef HPY_UNIVERSAL_ABI
#define _ht2hp(x) ((_HPyTracker_s *) (x)._i)
#define _hp2ht(x) ((HPyTracker) {(HPy_ssize_t) (hp)})
#else
#define _ht2hp(x) ((_HPyTracker_s *) (x)._o)
#define _hp2ht(x) ((HPyTracker) {(void *) (hp)})
#endif

static const HPy_ssize_t HPYTRACKER_INITIAL_SIZE = 5;

typedef struct {
    HPy_ssize_t size;
    HPy_ssize_t next;
    HPy *handles;
} _HPyTracker_s;


_HPy_HIDDEN HPyTracker
ctx_Tracker_New(HPyContext ctx, HPy_ssize_t size)
{
    _HPyTracker_s *hp;
    if (size == 0) {
        size = HPYTRACKER_INITIAL_SIZE;
    }
    size++;

    hp = PyMem_Malloc(sizeof(_HPyTracker_s));
    if (hp == NULL) {
        PyErr_NoMemory();
        return _hp2ht(0);
    }
    hp->handles = PyMem_Calloc(size, sizeof(HPy));
    if (hp->handles == NULL) {
        PyMem_Free(hp);
        PyErr_NoMemory();
        return _hp2ht(0);
    }
    hp->size = size;
    hp->next = 0;
    return _hp2ht(hp);
}

static int
tracker_resize(HPyContext ctx, _HPyTracker_s *hp, HPy_ssize_t size)
{
    HPy *new_handles;
    size++;

    if (size <= hp->next) {
        // refuse a resize that would either 1) lose handles or  2) not leave
        // space for one new handle
        PyErr_SetString(PyExc_ValueError, "HPyTracker resize would lose handles");
        return -1;
    }
    new_handles = PyMem_Realloc(hp->handles, size * sizeof(HPy));
    if (new_handles == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    hp->size = size;
    hp->handles = new_handles;
    return 0;
}

_HPy_HIDDEN int
ctx_Tracker_Add(HPyContext ctx, HPyTracker ht, HPy h)
{
    _HPyTracker_s *hp =  _ht2hp(ht);
    hp->handles[hp->next++] = h;
    if (hp->size <= hp->next) {
        if (tracker_resize(ctx, hp, hp->size * 2 - 1) < 0)
            return -1;
    }
    return 0;
}

_HPy_HIDDEN void
ctx_Tracker_ForgetAll(HPyContext ctx, HPyTracker ht)
{
    _HPyTracker_s *hp = _ht2hp(ht);
    hp->next = 0;
}

_HPy_HIDDEN void
ctx_Tracker_Close(HPyContext ctx, HPyTracker ht)
{
    _HPyTracker_s *hp = _ht2hp(ht);
    HPy_ssize_t i;
    for (i=0; i<hp->next; i++) {
        HPy_Close(ctx, hp->handles[i]);
    }
    PyMem_Free(hp->handles);
    PyMem_Free(hp);
}
