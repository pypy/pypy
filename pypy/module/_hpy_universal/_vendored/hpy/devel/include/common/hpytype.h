#ifndef HPY_UNIVERSAL_HPYTYPE_H
#define HPY_UNIVERSAL_HPYTYPE_H

#include <stdbool.h>

typedef struct {
    const char* name;
    bool has_pyobject_head;
    int basicsize;
    int itemsize;
    unsigned int flags;
    void *legacy_slots; // PyType_Slot *
    HPyDef *defines[];
} HPyType_Spec;

/* All types are dynamically allocated */
#define _Py_TPFLAGS_HEAPTYPE (1UL << 9)

/* Set if the type allows subclassing */
#define HPy_TPFLAGS_BASETYPE (1UL << 10)

#define HPy_TPFLAGS_DEFAULT _Py_TPFLAGS_HEAPTYPE

#define HPy_CAST(ctx, return_type, h) ((return_type *) _HPy_Cast(ctx, h))

#endif /* HPY_UNIVERSAL_HPYTYPE_H */
