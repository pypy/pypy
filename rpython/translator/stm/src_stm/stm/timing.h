/* Imported by rpython/translator/stm/import_stmgc.py */
#include <time.h>

static inline double get_stm_time(void)
{
    struct timespec tp;
    clock_gettime(CLOCK_MONOTONIC, &tp);
    return tp.tv_sec + tp.tv_nsec * 0.000000001;
}

static enum stm_time_e change_timing_state(enum stm_time_e newstate);
static void change_timing_state_tl(stm_thread_local_t *tl,
                                   enum stm_time_e newstate);

static void timing_end_transaction(enum stm_time_e attribute_to);
