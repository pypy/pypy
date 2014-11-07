/* Imported by rpython/translator/stm/import_stmgc.py */

struct finalizers_s {
    struct list_s *objects_with_finalizers;
    uintptr_t count_non_young;
    struct list_s *run_finalizers;
    uintptr_t *running_next;
};

static void mark_visit_from_finalizer_pending(void);
static void deal_with_young_objects_with_finalizers(void);
static void deal_with_old_objects_with_finalizers(void);
static void deal_with_objects_with_finalizers(void);

static void setup_finalizer(void);
static void teardown_finalizer(void);

static void _commit_finalizers(void);
static void abort_finalizers(struct stm_priv_segment_info_s *);

#define commit_finalizers()   do {              \
    if (STM_PSEGMENT->finalizers != NULL)       \
        _commit_finalizers();                   \
} while (0)


/* regular finalizers (objs from already-committed transactions) */
static struct finalizers_s g_finalizers;

static void _invoke_general_finalizers(stm_thread_local_t *tl);

#define invoke_general_finalizers(tl)    do {   \
    if (g_finalizers.run_finalizers != NULL)    \
        _invoke_general_finalizers(tl);         \
} while (0)

static void _execute_finalizers(struct finalizers_s *f);

#define any_local_finalizers() (STM_PSEGMENT->finalizers != NULL &&         \
                               STM_PSEGMENT->finalizers->run_finalizers != NULL)
#define exec_local_finalizers()  do {                   \
    if (any_local_finalizers())                         \
        _execute_finalizers(STM_PSEGMENT->finalizers);  \
} while (0)
