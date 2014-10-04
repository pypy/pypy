/* Imported by rpython/translator/stm/import_stmgc.py */

static void _timing_record_write(void);
static void _timing_fetch_inev(void);
static void _timing_contention(enum stm_event_e kind,
                               uint8_t other_segment_num, object_t *obj);


#define timing_event(tl, event)                                         \
    (stmcb_timing_event != NULL ? stmcb_timing_event(tl, event, NULL) : (void)0)

#define timing_record_write()                                           \
    (stmcb_timing_event != NULL ? _timing_record_write() : (void)0)

#define timing_fetch_inev()                                             \
    (stmcb_timing_event != NULL ? _timing_fetch_inev() : (void)0)

#define timing_contention(kind, other_segnum, obj)                      \
    (stmcb_timing_event != NULL ?                                       \
        _timing_contention(kind, other_segnum, obj) : (void)0)
