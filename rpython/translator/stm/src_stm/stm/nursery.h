/* Imported by rpython/translator/stm/import_stmgc.py */

/* '_stm_nursery_section_end' is either NURSERY_END or NSE_SIGxxx */
#define NSE_SIGPAUSE   STM_TIME_WAIT_OTHER
#define NSE_SIGCOMMITSOON   STM_TIME_SYNC_COMMIT_SOON


static uint32_t highest_overflow_number;

static void minor_collection(bool commit);
static void check_nursery_at_transaction_start(void);
static size_t throw_away_nursery(struct stm_priv_segment_info_s *pseg);
static void major_do_minor_collections(void);

#define must_abort()   is_abort(STM_SEGMENT->nursery_end)

static void assert_memset_zero(void *s, size_t n);

static object_t *find_shadow(object_t *obj);
