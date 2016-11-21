/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

static long mangle_hash(long i)
{
    /* To hash pointers in dictionaries.  Assumes that i shows some
       alignment (to 8, 16, maybe 32 bytes), so we use the following
       formula to avoid the trailing bits being always 0. */
    return i ^ (i >> 5);
}

static long id_or_identityhash(object_t *obj, bool is_hash)
{
    long result;

    if (obj != NULL) {
        if (_is_in_nursery(obj)) {
            obj = find_shadow(obj);
        }
        else if (is_hash) {
            if (obj->stm_flags & GCFLAG_HAS_SHADOW) {

                /* For identityhash(), we need a special case for some
                   prebuilt objects: their hash must be the same before
                   and after translation.  It is stored as an extra word
                   after the object.  But we cannot use it for id()
                   because the stored value might clash with a real one.
                */
                struct object_s *realobj = (struct object_s *)
                    REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
                size_t size = stmcb_size_rounded_up(realobj);
                result = *(long *)(((char *)realobj) + size);
                /* Important: the returned value is not mangle_hash()ed! */
                return result;
            }
        }
    }

    result = (long)(uintptr_t)obj;
    if (is_hash) {
        result = mangle_hash(result);
    }
    return result;
}

long stm_id(object_t *obj)
{
    return id_or_identityhash(obj, false);
}

long stm_identityhash(object_t *obj)
{
    return id_or_identityhash(obj, true);
}

void stm_set_prebuilt_identityhash(object_t *obj, long hash)
{
    struct object_s *realobj = (struct object_s *)
        get_virtual_address(STM_SEGMENT->segment_num, obj);

    assert(realobj->stm_flags == GCFLAG_WRITE_BARRIER);
    realobj->stm_flags |= GCFLAG_HAS_SHADOW;

    size_t size = stmcb_size_rounded_up(realobj);
    assert(*(long *)(((char *)realobj) + size) == 0);
    *(long *)(((char *)realobj) + size) = hash;
}
