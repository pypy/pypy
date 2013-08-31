/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_LISTS_H
#define _SRCSTM_LISTS_H

#include "dbgmem.h"

/************************************************************/

/* The g2l_xx functions ("global_to_local") are implemented as a tree,
   supporting very high performance in G2L_FIND in the common case where
   there are no or few elements in the tree, but scaling correctly
   if the number of items becomes large. */

#define TREE_BITS   4
#define TREE_ARITY  (1 << TREE_BITS)

#define TREE_DEPTH_MAX   ((sizeof(void*)*8 - 2 + TREE_BITS-1) / TREE_BITS)
/* sizeof(void*) = total number of bits
   2 = bits that we ignore anyway (2 or 3, conservatively 2)
   (x + TREE_BITS-1) / TREE_BITS = divide by TREE_BITS, rounding up
*/

#define TREE_MASK   ((TREE_ARITY - 1) * sizeof(void*))

typedef struct {
    gcptr addr;
    gcptr val;
} wlog_t;

typedef struct {
    char *items[TREE_ARITY];
} wlog_node_t;

struct G2L {
    char *raw_start, *raw_current, *raw_end;
    wlog_node_t toplevel;
};

void g2l_clear(struct G2L *g2l);
void g2l_delete(struct G2L *g2l);
static inline void g2l_delete_not_used_any_more(struct G2L *g2l) {
    stm_free(g2l->raw_start);
}

static inline int g2l_any_entry(struct G2L *g2l) {
    return g2l->raw_current != g2l->raw_start;
}

#define _G2L_LOOP(g2l, item, INITIAL, _PLUS_)                           \
{                                                                       \
  struct { char **next; char **end; } _stack[TREE_DEPTH_MAX], *_stackp; \
  char **_next, **_end, *_entry;                                        \
  long _deleted_factor = 0;                                             \
  struct G2L *_g2l = &(g2l);                                            \
  /* initialization */                                                  \
  _stackp = _stack;      /* empty stack */                              \
  _next = _g2l->toplevel.items + INITIAL;                               \
  _end = _next _PLUS_ TREE_ARITY;                                       \
  /* loop */                                                            \
  while (1)                                                             \
    {                                                                   \
      if (_next == _end)                                                \
        {                                                               \
          if (_stackp == _stack)                                        \
            break;   /* done */                                         \
          /* finished with this level, go to the next one */            \
          _stackp--;                                                    \
          _next = _stackp->next;                                        \
          _end = _stackp->end;                                          \
          continue;                                                     \
        }                                                               \
      _entry = *_next;                                                  \
      _next = _next _PLUS_ 1;                                           \
      if (_entry == NULL)   /* empty entry */                           \
        continue;                                                       \
      if (((long)_entry) & 1)                                           \
        {  /* points to a further level: enter it */                    \
          _stackp->next = _next;                                        \
          _stackp->end = _end;                                          \
          _stackp++;                                                    \
          _next = ((wlog_node_t *)(_entry - 1))->items + INITIAL;       \
          _end = _next _PLUS_ TREE_ARITY;                               \
          continue;                                                     \
        }                                                               \
      /* points to a wlog_t item */                                     \
      if (((wlog_t *)_entry)->addr == NULL) {   /* deleted entry */     \
          _deleted_factor += 3;                                         \
          continue;                                                     \
      }                                                                 \
      _deleted_factor -= 4;                                             \
      item = (wlog_t *)_entry;

#define G2L_LOOP_FORWARD(g2l, item)                             \
                       _G2L_LOOP(g2l, item, 0, +)
#define G2L_LOOP_BACKWARD(g2l, item)                            \
                       _G2L_LOOP(g2l, item, (TREE_ARITY-1), -)
#define G2L_LOOP_END     } }
#define G2L_LOOP_END_AND_COMPRESS                                       \
                         } if (_deleted_factor > 9) _g2l_compress(_g2l); }
#define G2L_LOOP_DELETE(item)  { (item)->addr = NULL; _deleted_factor += 6; }

#define G2L_FIND(g2l, addr1, result, goto_not_found)            \
{                                                               \
  revision_t _key = (revision_t)(addr1);                        \
  char *_p = (char *)((g2l).toplevel.items);                    \
  char *_entry = *(char **)(_p + (_key & TREE_MASK));           \
  if (_entry == NULL)                                           \
    goto_not_found;    /* common case, hopefully */             \
  result = _g2l_find(_entry, addr1);                            \
  if (result == NULL || result->addr != (addr1))                \
    goto_not_found;                                             \
}

wlog_t *_g2l_find(char *entry, gcptr addr);
void _g2l_compress(struct G2L *g2l);
void g2l_insert(struct G2L *g2l, gcptr addr, gcptr val);
void g2l_delete_item(struct G2L *g2l, gcptr addr);

static inline int g2l_contains(struct G2L *g2l, gcptr addr)
{
    wlog_t *result;
    G2L_FIND(*g2l, addr, result, return 0);
    return 1;
}

/************************************************************/

/* The gcptrlist_xx functions are implemented as an array that grows
   as needed. */

struct GcPtrList {
    long size, alloc;
    gcptr *items;
};

static inline void gcptrlist_clear(struct GcPtrList *gcptrlist) {
    gcptrlist->size = 0;
}

void gcptrlist_delete(struct GcPtrList *gcptrlist);
void gcptrlist_compress(struct GcPtrList *gcptrlist);
void _gcptrlist_grow(struct GcPtrList *gcptrlist);
void gcptrlist_insert2(struct GcPtrList *gcptrlist, gcptr newitem1,
                       gcptr newitem2);
void gcptrlist_insert3(struct GcPtrList *gcptrlist, gcptr newitem1,
                       gcptr newitem2, gcptr newitem3);

/* items[size++] = items[index]; items[index] = newitem; */
void gcptrlist_insert_at_index(struct GcPtrList *gcptrlist, long index,
                               gcptr newitem);

static inline void gcptrlist_insert(struct GcPtrList *gcptrlist, gcptr newitem)
{
    if (UNLIKELY(gcptrlist->size == gcptrlist->alloc))
        _gcptrlist_grow(gcptrlist);
    gcptrlist->items[gcptrlist->size++] = newitem;
}

static inline void gcptrlist_reduce_size(struct GcPtrList *gcptrlist, long nsz)
{
    gcptrlist->size = nsz;
}

static inline long gcptrlist_size(struct GcPtrList *gcptrlist)
{
    return gcptrlist->size;
}

static inline gcptr gcptrlist_pop(struct GcPtrList *gcptrlist)
{
    return gcptrlist->items[--gcptrlist->size];
}

void gcptrlist_merge(struct GcPtrList *, struct GcPtrList *gcptrlist_source);
void gcptrlist_move(struct GcPtrList *, struct GcPtrList *gcptrlist_source);

/************************************************************/

/* The fxcache_xx functions implement a fixed-size set of gcptr's.
   Moreover the gcptr's in the set are mapped to small integers.  In case
   of collisions, old items are discarded.  The cache doesn't use
   multi-way caching for now.

   The cache itself uses a total of FX_ENTRIES entries in the 'cache'
   array below, starting at 'shift'.  The reason it is bigger than
   necessary is that fxcache_clear() simply increments 'shift', making
   any previous entries invalid by not being in the correct position any
   more.
*/

//#define FX_MASK      65535    in stmgc.h
#define FX_ENTRIES   ((FX_MASK + 1) / sizeof(char *))
#define FX_TOTAL     (FX_ENTRIES * 4 / 3)

struct FXCache {
    revision_t shift;
    revision_t cache[FX_TOTAL];
};

extern __thread char *stm_read_barrier_cache;

void _fxcache_reset(struct FXCache *fxcache);

static inline void fxcache_clear(struct FXCache *fxcache)
{
    fxcache->shift++;
    if (fxcache->shift > FX_TOTAL - FX_ENTRIES)
        _fxcache_reset(fxcache);
    stm_read_barrier_cache = (char *)(fxcache->cache + fxcache->shift);
}

// moved to stmgc.h:
//#define FXCACHE_AT(obj)
//    (*(gcptr *)(stm_read_barrier_cache + ((revision_t)(obj) & FX_MASK)))

static inline void fxcache_add(struct FXCache *fxcache, gcptr newobj)
{
    assert(stm_read_barrier_cache == (char*)(fxcache->cache + fxcache->shift));
    FXCACHE_AT(newobj) = newobj;
}

static inline void fxcache_remove(struct FXCache *fxcache, gcptr oldobj)
{
    assert(stm_read_barrier_cache == (char*)(fxcache->cache + fxcache->shift));
    FXCACHE_AT(oldobj) = NULL;
}

/************************************************************/

#endif
