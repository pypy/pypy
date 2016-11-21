/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_NURSERY_H_
#define _STM_NURSERY_H_
#include <stdint.h>
#include <stdbool.h>

#define NSE_SIGPAUSE   _STM_NSE_SIGNAL_MAX
#define NSE_SIGABORT   _STM_NSE_SIGNAL_ABORT

static uint32_t highest_overflow_number;

static void _cards_cleared_in_object(struct stm_priv_segment_info_s *pseg, object_t *obj,
                                     bool strict);
static void _reset_object_cards(struct stm_priv_segment_info_s *pseg,
                                object_t *obj, uint8_t mark_value,
                                bool mark_all, bool really_clear);

static void minor_collection(bool commit, bool external);
static void check_nursery_at_transaction_start(void);
static void throw_away_nursery(struct stm_priv_segment_info_s *pseg);
static void major_do_validation_and_minor_collections(void);

static void assert_memset_zero(void *s, size_t n);


static inline bool is_abort(uintptr_t nursery_end) {
    return (nursery_end <= _STM_NSE_SIGNAL_MAX && nursery_end != NSE_SIGPAUSE);
}

static inline bool is_aborting_now(uint8_t other_segment_num) {
    return (is_abort(get_segment(other_segment_num)->nursery_end) &&
            get_priv_segment(other_segment_num)->safe_point != SP_RUNNING);
}

static inline bool will_allocate_in_nursery(size_t size_rounded_up) {
    OPT_ASSERT(size_rounded_up >= 16);
    OPT_ASSERT((size_rounded_up & 7) == 0);

    if (UNLIKELY(size_rounded_up >= _STM_FAST_ALLOC))
        return false;

    stm_char *p = STM_SEGMENT->nursery_current;
    stm_char *end = p + size_rounded_up;
    if (UNLIKELY((uintptr_t)end > STM_SEGMENT->nursery_end))
        return false;
    return true;
}


#define must_abort()   is_abort(STM_SEGMENT->nursery_end)
static object_t *find_shadow(object_t *obj);


#define GCWORD_MOVED  ((object_t *) -1)
static inline bool _is_young(object_t *obj);
static inline struct object_s *mark_loc(object_t *obj);
static inline bool _is_from_same_transaction(object_t *obj);

#endif
