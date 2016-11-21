/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_GCPAGE_H_
#define _STM_GCPAGE_H_
#include <stdbool.h>

/* Granularity when grabbing more unused pages: take 20 at a time */
#define GCPAGE_NUM_PAGES   20

/* More parameters fished directly from PyPy's default GC
   XXX document me */
#define GC_MIN                 (NB_NURSERY_PAGES * 4096 * 8)
#define GC_MAJOR_COLLECT       1.82

static struct list_s *testing_prebuilt_objs;
static char *uninitialized_page_start;   /* within segment 0 */
static char *uninitialized_page_stop;

static void setup_gcpage(void);
static void teardown_gcpage(void);
static void setup_N_pages(char *pages_addr, long num);
static stm_char *allocate_outside_nursery_large(uint64_t size);


static void major_collection_if_requested(void);
static void major_collection_now_at_safe_point(void);
static void major_collection_with_mutex(void);
static bool largemalloc_keep_object_at(char *data);   /* for largemalloc.c */
static bool smallmalloc_keep_object_at(char *data);   /* for smallmalloc.c */

static inline bool mark_visited_test(object_t *obj);
static bool is_overflow_obj_safe(struct stm_priv_segment_info_s *pseg, object_t *obj);
static void mark_visit_possibly_overflow_object(object_t *obj, struct stm_priv_segment_info_s *pseg);

#endif
