/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

static struct list_s *prebuilt_objects_to_trace;
static struct tree_s *tree_prebuilt_objs;  /* XXX from gcpage.c */


static void prebuilt_trace(object_t **pstaticobj_invalid)
{
    uintptr_t objaddr = (uintptr_t)*pstaticobj_invalid;
    struct object_s *obj = (struct object_s *)objaddr;

    if (obj == NULL)
        return;

    /* If the object was already moved, it is stored in 'tree_prebuilt_objs'.
       For now we use this dictionary, with keys being equal to the numeric
       address of the prebuilt object.
     */
    wlog_t *item;
    TREE_FIND(tree_prebuilt_objs, (uintptr_t)obj, item, goto not_found);

    *pstaticobj_invalid = (object_t *)item->val;    /* already moved */
    return;

 not_found:;
    /* We need to make a copy of this object.  The extra "long" is for
       the prebuilt hash. */
    size_t size = stmcb_size_rounded_up(obj);
    object_t *nobj = _stm_allocate_old(size + sizeof(long));

    /* Copy the object */
    char *realnobj = get_virtual_address(STM_SEGMENT->segment_num, nobj);
    memcpy(realnobj, (char *)objaddr, size);

    /* Fix the flags in the copied object, asserting that it was zero so far */
    assert(nobj->stm_flags == 0);
    nobj->stm_flags = GCFLAG_WRITE_BARRIER;

    /* Add the object to the tree */
    tree_insert(tree_prebuilt_objs, (uintptr_t)obj, (uintptr_t)nobj);

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
    if (tree_prebuilt_objs == NULL)
        tree_prebuilt_objs = tree_create();

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
