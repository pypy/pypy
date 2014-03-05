/* Imported by rpython/translator/stm/import_stmgc.py */

static void write_write_contention_management(uintptr_t lock_idx);
static void write_read_contention_management(uint8_t other_segment_num);
static void inevitable_contention_management(uint8_t other_segment_num);

static inline bool is_aborting_now(uint8_t other_segment_num) {
    return (get_segment(other_segment_num)->nursery_end == NSE_SIGABORT &&
            get_priv_segment(other_segment_num)->safe_point != SP_RUNNING);
}
