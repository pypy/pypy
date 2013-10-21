/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_NURSERY_H
#define _SRCSTM_NURSERY_H

#ifndef GC_NURSERY
#define GC_NURSERY        4190208    /* 4 MB - 4 kb */
//#define GC_NURSERY        (1<<20)    /* 1 MB */
#endif

#ifndef GC_NURSERY_SECTION
# if GC_NURSERY >= 2 * 135168
#  define GC_NURSERY_SECTION    135168
# else
#  define GC_NURSERY_SECTION    (GC_NURSERY / 2)
# endif
#endif

#if GC_NURSERY % GC_NURSERY_SECTION != 0
# error "GC_NURSERY must be a multiple of GC_NURSERY_SECTION"
#endif

#define END_MARKER_OFF  ((gcptr) 16)
#define END_MARKER_ON   ((gcptr) 24)


#define NURSERY_FIELDS_DECL                                             \
    /* the nursery */                                                   \
    char **nursery_current_ref;                                         \
    char **nursery_nextlimit_ref;                                       \
    char *nursery_end;                                                  \
    char *nursery_base;                                                 \
    enum { NC_REGULAR, NC_ALREADY_CLEARED } nursery_cleared;            \
                                                                        \
    /* Between collections, we add to 'old_objects_to_trace' the        \
       private objects that are old but may contain pointers to         \
       young objects.  During minor collections the same list is        \
       used to record all other old objects pending tracing; in         \
       other words minor collection is a process that works             \
       until the list is empty again. */                                \
    struct GcPtrList old_objects_to_trace;                              \
                                                                        \
    /* 'public_with_young_copy' is a list of all public objects         \
       that are outdated and whose 'h_revision' points to a             \
       young object. */                                                 \
    struct GcPtrList public_with_young_copy;                            \
                                                                        \
    /* These numbers are initially zero, but after a minor              \
       collection, they are set to the size of the two lists            \
       'private_from_protected' and 'list_of_read_objects'.             \
       It's used on the following minor collection, if we're            \
       still in the same transaction, to know that the initial          \
       part of the lists cannot contain young objects any more. */      \
    long num_private_from_protected_known_old;                          \
    long num_read_objects_known_old;                                    \
                                                                        \
    /* Weakref support */                                               \
    struct GcPtrList young_weakrefs;


struct tx_descriptor;  /* from et.h */
extern __thread char *stm_nursery_current;
extern __thread char *stm_nursery_nextlimit;


void stmgc_init_nursery(void);
void stmgc_done_nursery(void);
void stmgc_minor_collect(void);
void stmgc_minor_collect_no_abort(void);
gcptr stmgc_duplicate(gcptr);
gcptr stmgc_duplicate_old(gcptr);
size_t stmgc_size(gcptr);
void stmgc_trace(gcptr, void visit(gcptr *));
void stmgc_minor_collect_soon(void);
int stmgc_is_in_nursery(struct tx_descriptor *d, gcptr obj);

#endif
