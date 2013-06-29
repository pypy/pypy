/* Imported by rpython/translator/stm/import_stmgc.py: 45380d4cb89c */
#ifndef _SRCSTM_GCPAGE_H
#define _SRCSTM_GCPAGE_H


#define WORD                sizeof(gcptr)
#define GC_SMALL_REQUESTS   36

#define DEBUG_WORD(char)    (revision_t)(((char) *                      \
                                      (WORD >= 8 ? 0x0101010101010101ULL \
                                                 : 0x01010101ULL)))


/* Linux's glibc is good at 'malloc(1023*WORD)': the blocks ("pages") it
   returns are exactly 1024 words apart, reserving only one extra word
   for its internal data.  Here we assume that even on other systems it
   will not use more than three words.  It results in pages of 1020
   WORDs, which is a number that divides well by many small values. */
#ifndef GC_PAGE_SIZE
#define GC_PAGE_SIZE   (1021 * WORD)
#endif

/* This is the largest size that we will map to our internal "pages"
   structures. */
#define GC_SMALL_REQUEST_THRESHOLD   ((GC_SMALL_REQUESTS-1) * WORD)

/* The minimum heap size: never run a full collection with a smaller heap. */
#ifndef GC_MIN
#define GC_MIN    (16 * 1024 * 1024)
#endif

/* The minimum expansion factor: never run a full collection before we have
   allocated this much space. */
#ifndef GC_EXPAND
#define GC_EXPAND    (7 * 1024 * 1024)
#endif

/* The heap is collected when it reaches 1.82 times what it had before. */
#define GC_MAJOR_COLLECT    1.82


typedef struct page_header_s {
    struct page_header_s *next_page;
} page_header_t;


/* These fields are in tx_public_descriptor rather than tx_descriptor.
   The indirection allows us to keep around the lists of pages even
   after the thread finishes, until the next major collection.
*/
#define GCPAGE_FIELDS_DECL                                              \
    /* The array 'pages_for_size' contains GC_SMALL_REQUESTS            \
       chained lists of pages currently managed by this thread.         \
       For each size N between WORD and SMALL_REQUEST_THRESHOLD         \
       (included), the corresponding chained list contains pages        \
       which store objects of size N. */                                \
    struct page_header_s *pages_for_size[GC_SMALL_REQUESTS];            \
                                                                        \
    /* This array contains GC_SMALL_REQUESTS chained lists of           \
       free locations. */                                               \
    gcptr free_loc_for_size[GC_SMALL_REQUESTS];                         \
                                                                        \
    /* For statistics */                                                \
    size_t count_pages;                                                 \
                                                                        \
    /* A set of all non-small objects (outside the nursery).            \
       We could also have a single global set, but this avoids          \
       locking in stmgcpage_malloc/free. */                             \
    struct G2L nonsmall_objects;


#define LOCAL_GCPAGES()  (thread_descriptor->public_descriptor)


void stmgcpage_acquire_global_lock(void);
void stmgcpage_release_global_lock(void);
void stmgcpage_init_tls(void);   /* must hold the global lock */
void stmgcpage_done_tls(void);   /* must hold the global lock */
gcptr stmgcpage_malloc(size_t size);
void stmgcpage_free(gcptr obj);
void stmgcpage_add_prebuilt_root(gcptr obj);
void stmgcpage_possibly_major_collect(int force);
long stmgcpage_count(int quantity);

extern struct GcPtrList stm_prebuilt_gcroots;

#endif
