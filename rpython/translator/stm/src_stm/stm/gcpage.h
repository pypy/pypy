/* Imported by rpython/translator/stm/import_stmgc.py */

/* Granularity when grabbing more unused pages: take 20 at a time */
#define GCPAGE_NUM_PAGES   20

/* More parameters fished directly from PyPy's default GC
   XXX document me */
#define GC_MIN                 (NB_NURSERY_PAGES * 4096 * 8)
#define GC_MAJOR_COLLECT       1.82



static char *uninitialized_page_start;   /* within segment 0 */
static char *uninitialized_page_stop;

static void setup_gcpage(void);
static void teardown_gcpage(void);
static void setup_N_pages(char *pages_addr, long num);
static stm_char *allocate_outside_nursery_large(uint64_t size);


static void major_collection_if_requested(void);
static void major_collection_now_at_safe_point(void);
static bool largemalloc_keep_object_at(char *data);   /* for largemalloc.c */
static bool smallmalloc_keep_object_at(char *data);   /* for smallmalloc.c */
