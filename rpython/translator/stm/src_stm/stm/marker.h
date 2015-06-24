/* Imported by rpython/translator/stm/import_stmgc.py */
static void _timing_record_write_position(void);
static void timing_write_read_contention(struct stm_undo_s *start,
                                         struct stm_undo_s *contention);
static void _timing_become_inevitable(void);


#define timing_enabled()   (stmcb_timing_event != NULL)

#define timing_event(tl, event)                                         \
    (timing_enabled() ? stmcb_timing_event(tl, event, NULL) : (void)0)

#define timing_record_write_position()                                  \
    (timing_enabled() ? _timing_record_write_position() : (void)0)

#define timing_become_inevitable()                                      \
    (timing_enabled() ? _timing_become_inevitable() : (void)0)


static inline void emit_wait(stm_thread_local_t *tl, enum stm_event_e event)
{
    if (!timing_enabled())
        return;
    if (tl->wait_event_emitted != 0) {
        if (tl->wait_event_emitted == event)
            return;
        stmcb_timing_event(tl, STM_WAIT_DONE, NULL);
    }
    tl->wait_event_emitted = event;
    stmcb_timing_event(tl, event, NULL);
}

static inline void emit_wait_done(stm_thread_local_t *tl)
{
    if (tl->wait_event_emitted != 0) {
        tl->wait_event_emitted = 0;
        stmcb_timing_event(tl, STM_WAIT_DONE, NULL);
    }
}

#define EMIT_WAIT(event)  emit_wait(STM_SEGMENT->running_thread, event)
#define EMIT_WAIT_DONE()  emit_wait_done(STM_SEGMENT->running_thread)
