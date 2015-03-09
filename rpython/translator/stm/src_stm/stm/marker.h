/* Imported by rpython/translator/stm/import_stmgc.py */
static void _timing_record_write_position(void);
static void timing_write_read_contention(struct stm_undo_s *start,
                                         struct stm_undo_s *contention);
static void _timing_record_inev_position(void);
static void _timing_commit_inev_position(void);
static void timing_wait_other_inevitable(void);


#define timing_enabled()   (stmcb_timing_event != NULL)

#define timing_event(tl, event)                                         \
    (timing_enabled() ? stmcb_timing_event(tl, event, NULL) : (void)0)

#define timing_record_write_position()                                  \
    (timing_enabled() ? _timing_record_write_position() : (void)0)

#define timing_record_inev_position()                                   \
    (timing_enabled() ? _timing_record_inev_position() : (void)0)

#define timing_commit_inev_position()                                   \
    (timing_enabled() ? _timing_commit_inev_position() : (void)0)
