/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


char *_stm_real_address(object_t *o)
{
    if (o == NULL)
        return NULL;

    assert(FIRST_OBJECT_PAGE * 4096UL <= (uintptr_t)o
           && (uintptr_t)o < NB_PAGES * 4096UL);
    return REAL_ADDRESS(STM_SEGMENT->segment_base, o);
}

char *_stm_get_segment_base(long index)
{
    return get_segment_base(index);
}

struct stm_priv_segment_info_s *_stm_segment(void)
{
    char *info = REAL_ADDRESS(STM_SEGMENT->segment_base, STM_PSEGMENT);
    return (struct stm_priv_segment_info_s *)info;
}

stm_thread_local_t *_stm_thread(void)
{
    return STM_SEGMENT->running_thread;
}

bool _stm_was_read(object_t *obj)
{
    return was_read_remote(STM_SEGMENT->segment_base, obj,
                           STM_SEGMENT->transaction_read_version);
}

bool _stm_was_written(object_t *obj)
{
    return (obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) == 0;
}


bool _stm_was_written_card(object_t *obj)
{
    return obj->stm_flags & _STM_GCFLAG_CARDS_SET;
}

#ifdef STM_TESTS
uintptr_t _stm_get_private_page(uintptr_t pagenum)
{
    /* xxx returns 0 or 1 now */
    return is_private_page(STM_SEGMENT->segment_num, pagenum);
}

long _stm_count_modified_old_objects(void)
{
    if (STM_PSEGMENT->modified_old_objects == NULL)
        return -1;
    return list_count(STM_PSEGMENT->modified_old_objects);
}

long _stm_count_objects_pointing_to_nursery(void)
{
    if (STM_PSEGMENT->objects_pointing_to_nursery == NULL)
        return -1;
    return list_count(STM_PSEGMENT->objects_pointing_to_nursery);
}

long _stm_count_old_objects_with_cards(void)
{
    if (STM_PSEGMENT->old_objects_with_cards == NULL)
        return -1;
    return list_count(STM_PSEGMENT->old_objects_with_cards);
}

object_t *_stm_enum_modified_old_objects(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->modified_old_objects, index);
}

object_t *_stm_enum_objects_pointing_to_nursery(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->objects_pointing_to_nursery, index);
}

object_t *_stm_enum_old_objects_with_cards(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->old_objects_with_cards, index);
}

uint64_t _stm_total_allocated(void)
{
    return increment_total_allocated(0);
}
#endif
