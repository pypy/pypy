/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


#define GCWORD_PREBUILT_MOVED  ((object_t *) 42)

static struct list_s *prebuilt_objects_to_trace;


static void prebuilt_trace(object_t **pstaticobj_invalid)
{
    uintptr_t objaddr = (uintptr_t)*pstaticobj_invalid;
    struct object_s *obj = (struct object_s *)objaddr;

    if (obj == NULL)
        return;

    /* If the object was already moved, its first word was set to
       GCWORD_PREBUILT_MOVED.  In that case, the forwarding location,
       i.e. where the object moved to, is stored in the second word.
    */
    object_t **pforwarded_array = (object_t **)objaddr;

    if (pforwarded_array[0] == GCWORD_PREBUILT_MOVED) {
        *pstaticobj_invalid = pforwarded_array[1];    /* already moved */
        return;
    }

    /* We need to make a copy of this object.  The extra "long" is for
       the prebuilt hash. */
    size_t size = stmcb_size_rounded_up(obj);
    object_t *nobj = _stm_allocate_old(size + sizeof(long));

    /* Copy the object */
    char *realnobj = REAL_ADDRESS(stm_object_pages, nobj);
    memcpy(realnobj, (char *)objaddr, size);

    /* Fix the flags in the copied object, asserting that it was zero so far */
    assert(nobj->stm_flags == 0);
    nobj->stm_flags = GCFLAG_WRITE_BARRIER;

    /* Mark the original object */
    pforwarded_array[0] = GCWORD_PREBUILT_MOVED;
    pforwarded_array[1] = nobj;

    /* Done */
    *pstaticobj_invalid = nobj;
    LIST_APPEND(prebuilt_objects_to_trace, realnobj);
}

object_t *stm_setup_prebuilt(object_t *staticobj_invalid)
{
    /* All variable names in "_invalid" here mean that although the
       type is really "object_t *", it should not actually be accessed
       via %gs.
    */
    LIST_CREATE(prebuilt_objects_to_trace);

    object_t *obj = staticobj_invalid;
    prebuilt_trace(&obj);

    while (!list_is_empty(prebuilt_objects_to_trace)) {
        struct object_s *realobj1 =
            (struct object_s *)list_pop_item(prebuilt_objects_to_trace);
        stmcb_trace(realobj1, &prebuilt_trace);
    }

    LIST_FREE(prebuilt_objects_to_trace);

    return obj;
}
