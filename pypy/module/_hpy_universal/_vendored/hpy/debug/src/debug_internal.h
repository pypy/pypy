/* Internal header for all the files in hpy/debug/src. The public API is in
   include/hpy_debug.h
*/
#ifndef HPY_DEBUG_INTERNAL_H
#define HPY_DEBUG_INTERNAL_H

#include <assert.h>
#include "hpy.h"
#include "hpy_debug.h"

#define HPY_DEBUG_MAGIC 0xDEB00FF

/* The Debug context is a wrapper around an underlying context, which we will
   call Universal. Inside the debug mode we manipulate handles which belongs
   to both contexts, so to make things easier we create two typedefs to make
   it clear what kind of handle we expect: UHPy and DHPy:

     * UHPy are opaque from our point of view.

     * DHPy are actually DebugHandle* in disguise. DebugHandles are wrappers
       around a UHPy, with a bunch of extra info.

   To cast between DHPy and DebugHandle*, use as_DebugHandle and as_DHPy:
   these are just no-op casts.

   Each DHPy wraps a corresponding UHPy: DHPys are created by calling
   DHPy_open, and they must be eventually closed by DHPy_close. Note that if
   you call DHPy_open twice on the same UHPy, you get two different DHPy.

   To unwrap a DHPy and get the underlying UHPy, call DHPy_unwrap. If you call
   DHPy_unwrap multiple times on the same DHPy, you always get the same UHPy.

   WARNING: both UHPy and DHPy are alias of HPy, so we need to take care of
   not mixing them, because the compiler cannot help.

   Each DebugHandle has a "generation", which is just an int to be able to get
   only the handles which were created after a certain point.

   DHPys/DebugHandles are memory-managed by using a free list:

     - info->open_handles is a list of all DHPys which are currently open

     - DHPy_close() moves a DHPy from info->open_handles to info->closed_handles

     - if closed_handles is too big, the oldest DHPy is freed by DHPy_free()

     - to allocate memory for a new DHPy, DHPy_open() does the following:

         * if closed_handles is full, it reuses the memory of the oldest DHPy
           in the queue

         * else, it malloc()s memory for a new DHPy


   Each DebugHandle can have some "raw" data associated with it. It is a
   generic pointer to any data. The validity, or life-time, of such pointer
   is supposed to be the same as the that of the handle and the debug mode
   enforces it. Additionally, the data can be also marked as write protected.

   Example is the `const char*` handed out by `HPyUnicode_AsUTF8AndSize`. It
   must not be written by the user (users may discard the const modifier), and
   the pointer is considered invalid once the handle is closed, so it must not
   be accessed even for reading. Most Python implementations, will choose to
   hand out pointer to the actual internal data, which happen to stay valid and
   accessible and this may lead the users to a wrong conclusion that they can
   use the pointer after the handle is closed.

   The memory protection mechanism is abstracted by several functions that
   may have different implementations depending on the compile-time
   configuration. Those are:

   * `raw_data_copy`: makes a copy of some data, optionally the copy can be
                      made read-only.
   * `raw_data_protect`: protects the result of `raw_data_copy` from reading
   * `raw_data_free`: if `raw_data_protect` retained any actual memory or other
                      resources, this indicates that those can be freed

   Any HPy context function that wishes to attach raw data to a handle should
   make a copy of the actual data by using `raw_data_copy`. This copy should be
   then set as the value of the associated_data field. Once the handle is
   closed, the raw data pointer is passed to raw_data_protect and once the handle
   is reused the raw data pointer is passed to raw_data_free.

   This means that if the implementation of `raw_data_protect` retains some
   resources, we are leaking them. To mitigate this a bit, we have a limit on the
   overall size of data that can be leaked and once it is reached, we use
   raw_data_free immediately once the associated handle is closed.

   Note that, for example, the mmap based implementation of `raw_data_copy`
   never allocates less than a page, so it actually takes more memory than
   what is the size of the raw data. This is, however, mostly covered by the
   limit on closed handles. For the default configuration we have:

   DEFAULT_CLOSED_HANDLES_QUEUE_MAX_SIZE = 1024
   DEFAULT_PROTECTED_RAW_DATA_MAX_SIZE = 1024 * 1024 * 10

   the total leaked raw data size limit of 10MB is larger than if we created
   and leaked 1024 handles with only a small raw data attached to them (4MB
   for 1024 pages of 4KB). This ratio may be different for larger pages or for
   different configuration of the limits. For the sake of keeping the
   implementation reasonably simple and portable, we choose to ignore this
   for the time being.
*/

typedef HPy UHPy;
typedef HPy DHPy;

/* Under CPython:
     - UHPy always end with 1 (see hpy.universal's _py2h and _h2py)
     - DHPy are pointers, so they always end with 0

   DHPy_sanity_check is a minimal check to ensure that we are not treating a
   UHPy as a DHPy. Note that DHPy_sanity_check works fine also on HPy_NULL.

   NOTE: UHPy_sanity_check works ONLY with CPython's hpy.universal, because
   UHPys are computed in such a way that the last bit it's always 1. On other
   implementations this assumption might not hold. By default,
   UHPy_sanity_check does nothing, unless you #define
   HPY_DEBUG_ENABLE_UHPY_SANITY_CHECK, which for CPython is done by setup.py
*/
static inline void DHPy_sanity_check(DHPy dh) {
    assert( (dh._i & 1) == 0 );
}

static inline void UHPy_sanity_check(UHPy uh) {
#ifdef HPY_DEBUG_ENABLE_UHPY_SANITY_CHECK
    if (!HPy_IsNull(uh))
        assert( (uh._i & 1) == 1 );
#endif
}

// NOTE: having a "generation" field is the easiest way to know when a handle
// was created, but we waste 8 bytes per handle. Since all handles of the same
// generation are stored sequentially in the open_handles list, a possible
// alternative implementation is to put special placeholders inside the list
// to mark the creation of a new generation
typedef struct DebugHandle {
    UHPy uh;
    long generation;
    bool is_closed;
    // pointer to and size of any raw data associated with
    // the lifetime of the handle:
    void *associated_data;
    HPy_ssize_t associated_data_size;
    struct DebugHandle *prev;
    struct DebugHandle *next;
} DebugHandle;

static inline DebugHandle * as_DebugHandle(DHPy dh) {
    DHPy_sanity_check(dh);
    return (DebugHandle *)dh._i;
}

static inline DHPy as_DHPy(DebugHandle *handle) {
    return (DHPy){(HPy_ssize_t)handle};
}

DHPy DHPy_open(HPyContext *dctx, UHPy uh);
void DHPy_close(HPyContext *dctx, DHPy dh);
void DHPy_close_and_check(HPyContext *dctx, DHPy dh);
void DHPy_free(HPyContext *dctx, DHPy dh);
void DHPy_invalid_handle(HPyContext *dctx, DHPy dh);

static inline UHPy DHPy_unwrap(HPyContext *dctx, DHPy dh)
{
    if (HPy_IsNull(dh))
        return HPy_NULL;
    DebugHandle *handle = as_DebugHandle(dh);
    if (handle->is_closed)
        DHPy_invalid_handle(dctx, dh);
    return handle->uh;
}

/* === DHQueue === */

typedef struct {
    DebugHandle *head;
    DebugHandle *tail;
    HPy_ssize_t size;
} DHQueue;

void DHQueue_init(DHQueue *q);
void DHQueue_append(DHQueue *q, DebugHandle *h);
DebugHandle *DHQueue_popfront(DHQueue *q);
void DHQueue_remove(DHQueue *q, DebugHandle *h);
void DHQueue_sanity_check(DHQueue *q);

/* === HPyDebugInfo === */

static const HPy_ssize_t DEFAULT_CLOSED_HANDLES_QUEUE_MAX_SIZE = 1024;
static const HPy_ssize_t DEFAULT_PROTECTED_RAW_DATA_MAX_SIZE = 1024 * 1024 * 10;

typedef struct {
    long magic_number; // used just for sanity checks
    HPyContext *uctx;
    long current_generation;

    // the following should be an HPyField, but it's complicate:
    // HPyFields should be used only on memory which is known by the GC, which
    // happens automatically if you use e.g. HPy_New, but currently
    // HPy_DebugInfo is malloced(). We need either:
    //   1. a generic HPy_GcMalloc() OR
    //   2. HPy_{Un}TrackMemory(), so that we can add manually allocated
    //      memory as a GC root
    UHPy uh_on_invalid_handle;
    HPy_ssize_t closed_handles_queue_max_size; // configurable by the user
    HPy_ssize_t protected_raw_data_max_size;
    HPy_ssize_t protected_raw_data_size;
    DHQueue open_handles;
    DHQueue closed_handles;
} HPyDebugInfo;

static inline HPyDebugInfo *get_info(HPyContext *dctx)
{
    HPyDebugInfo *info = (HPyDebugInfo*)dctx->_private;
    assert(info->magic_number == HPY_DEBUG_MAGIC); // sanity check
    return info;
}


void *raw_data_copy(const void* data, HPy_ssize_t size, bool write_protect);
void raw_data_protect(void* data, HPy_ssize_t size);
/* Return value: 0 indicates success, any different value indicates an error */
int raw_data_free(void *data, HPy_ssize_t size);

#endif /* HPY_DEBUG_INTERNAL_H */
