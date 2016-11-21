/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
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
    return get_segment_base(index+1);
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
    return was_read_remote(STM_SEGMENT->segment_base, obj);
}

bool _stm_was_written(object_t *obj)
{
    return (obj->stm_flags & _STM_GCFLAG_WRITE_BARRIER) == 0;
}

bool _stm_was_written_card(object_t *obj)
{
    return obj->stm_flags & _STM_GCFLAG_CARDS_SET;
}

long _stm_count_cl_entries(void)
{
    struct stm_commit_log_entry_s *cl = &commit_log_root;

    long count = 0;
    while ((cl = cl->next)) {
        if (cl == INEV_RUNNING)
            break;
        count++;
    }
    return count;
}


#ifdef STM_TESTS
bool _stm_is_accessible_page(uintptr_t pagenum)
{
    acquire_privatization_lock(STM_SEGMENT->segment_num);
    bool res = get_page_status_in(STM_SEGMENT->segment_num, pagenum) == PAGE_ACCESSIBLE;
    release_privatization_lock(STM_SEGMENT->segment_num);
    return res;
}

long _stm_count_modified_old_objects(void)
{
    assert(STM_PSEGMENT->modified_old_objects);
    assert(list_count(STM_PSEGMENT->modified_old_objects) < 30000);
    assert((list_count(STM_PSEGMENT->modified_old_objects) % 3) == 0);
    return list_count(STM_PSEGMENT->modified_old_objects) / 3;
}

long _stm_count_objects_pointing_to_nursery(void)
{
    if (STM_PSEGMENT->objects_pointing_to_nursery == NULL)
        return -1;
    return list_count(STM_PSEGMENT->objects_pointing_to_nursery);
}

long _stm_count_old_objects_with_cards_set(void)
{
    if (STM_PSEGMENT->old_objects_with_cards_set == NULL)
        return -1;
    return list_count(STM_PSEGMENT->old_objects_with_cards_set);
}

object_t *_stm_enum_modified_old_objects(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->modified_old_objects, index * 3);
}

object_t *_stm_enum_objects_pointing_to_nursery(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->objects_pointing_to_nursery, index);
}

object_t *_stm_enum_old_objects_with_cards_set(long index)
{
    return (object_t *)list_item(
        STM_PSEGMENT->old_objects_with_cards_set, index);
}


uint8_t _stm_get_card_value(object_t *obj, long idx)
{
    struct stm_read_marker_s *cards = get_read_marker(STM_SEGMENT->segment_base,
                                                      (uintptr_t)obj);
    return cards[get_index_to_card_index(idx)].rm;
}

uint8_t _stm_get_transaction_read_version(void)
{
    return STM_SEGMENT->transaction_read_version;
}



static struct stm_commit_log_entry_s *_last_cl_entry;
static long _last_cl_entry_index;
void _stm_start_enum_last_cl_entry(void)
{
    _last_cl_entry = &commit_log_root;
    struct stm_commit_log_entry_s *cl = &commit_log_root;

    while ((cl = cl->next)) {
        _last_cl_entry = cl;
    }
    _last_cl_entry_index = 0;
}

object_t *_stm_next_last_cl_entry(void)
{
    if (_last_cl_entry == &commit_log_root)
        return NULL;
    if (_last_cl_entry_index >= _last_cl_entry->written_count)
        return NULL;
    return _last_cl_entry->written[_last_cl_entry_index++].object;
}

uint64_t _stm_total_allocated(void)
{
    return increment_total_allocated(0);
}


void _stm_smallmalloc_sweep_test(void)
{
    acquire_all_privatization_locks();
    _stm_smallmalloc_sweep();
    release_all_privatization_locks();
}

#endif
