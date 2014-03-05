/* Imported by rpython/translator/stm/import_stmgc.py */

/* '_stm_nursery_section_end' is either NURSERY_END or NSE_SIGxxx */
#define NSE_SIGPAUSE   0
#define NSE_SIGABORT   1
#if     NSE_SIGABORT > _STM_NSE_SIGNAL_MAX
#  error "update _STM_NSE_SIGNAL_MAX"
#endif


static uint32_t highest_overflow_number;

static void minor_collection(bool commit);
static void check_nursery_at_transaction_start(void);
static void throw_away_nursery(struct stm_priv_segment_info_s *pseg);
static void major_do_minor_collections(void);

static inline bool must_abort(void) {
    return STM_SEGMENT->nursery_end == NSE_SIGABORT;
}

static void assert_memset_zero(void *s, size_t n);

static object_t *find_shadow(object_t *obj);
