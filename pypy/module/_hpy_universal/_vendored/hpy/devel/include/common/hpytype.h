#ifndef HPY_UNIVERSAL_HPYTYPE_H
#define HPY_UNIVERSAL_HPYTYPE_H

#include <stdbool.h>

/* To be able to be compatible with CPython (in both CPython and Universal ABI
   modes) we need to reserve some space at the beginning of user-defined
   structs which will contain ob_refcnt and ob_type. However, HPy users should
   not be able to access them directly.

   Alternate implementations are free to use this extra space as they
   want. Moreover, if they do NOT need this extra space, they can avoid
   wasting memory by allocating sizeof(_HPyObject_head_s) bytes less inside
   their implementation of HPy_New.
*/


struct _HPyObject_head_s {
    HPy_ssize_t _reserved0;
    void *_reserved1;
};
#define HPyObject_HEAD struct _HPyObject_head_s _ob_head;


typedef struct {
    const char* name;
    int basicsize;
    int itemsize;
    unsigned int flags;
    void *legacy_slots; // PyType_Slot *
    HPyDef **defines;   /* points to an array of 'HPyDef *' */
} HPyType_Spec;

typedef enum {
    HPyType_SpecParam_Base = 1,
    HPyType_SpecParam_BasesTuple = 2,
    //HPyType_SpecParam_Metaclass = 3,
    //HPyType_SpecParam_Module = 4,
} HPyType_SpecParam_Kind;

typedef struct {
    HPyType_SpecParam_Kind kind;
    HPy object;
} HPyType_SpecParam;

/* All types are dynamically allocated */
#define _Py_TPFLAGS_HEAPTYPE (1UL << 9)

/* Set if the type allows subclassing */
#define HPy_TPFLAGS_BASETYPE (1UL << 10)

#define HPy_TPFLAGS_DEFAULT _Py_TPFLAGS_HEAPTYPE

#define HPy_CAST(ctx, return_type, h) ((return_type *) _HPy_Cast(ctx, h))

#endif /* HPY_UNIVERSAL_HPYTYPE_H */
