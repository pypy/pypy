/* Imported by rpython/translator/stm/import_stmgc.py */
static void _timing_record_write_position(void);
static void timing_write_read_contention(struct stm_undo_s *start,
                                         struct stm_undo_s *contention);


#define timing_event(tl, event)                                         \
    (stmcb_timing_event != NULL ? stmcb_timing_event(tl, event, NULL) : (void)0)

#define timing_record_write_position()                                  \
    (stmcb_timing_event != NULL ? _timing_record_write_position() : (void)0)
