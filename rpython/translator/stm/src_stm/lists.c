/* -*- c-basic-offset: 2 -*- */

#include <limits.h>

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

static void _g2l_clear_node(wlog_node_t *node)
{
  memset(node, 0, sizeof(wlog_node_t));
}

static void g2l_clear(struct G2L *g2l)
{
  if (g2l->raw_current != g2l->raw_start)
    {
      _g2l_clear_node(&g2l->toplevel);
      g2l->raw_current = g2l->raw_start;
    }
}

static int g2l_any_entry(struct G2L *g2l)
{
  return g2l->raw_current != g2l->raw_start;
}

#define _G2L_LOOP(g2l, item, INITIAL, _PLUS_)                           \
{                                                                       \
  struct { char **next; char **end; } _stack[TREE_DEPTH_MAX], *_stackp; \
  char **_next, **_end, *_entry;                                        \
  /* initialization */                                                  \
  _stackp = _stack;      /* empty stack */                              \
  _next = (g2l).toplevel.items + INITIAL;                               \
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
      item = (wlog_t *)_entry;

#define G2L_LOOP_FORWARD(g2l, item)                             \
                       _G2L_LOOP(g2l, item, 0, +)
#define G2L_LOOP_BACKWARD(g2l, item)                            \
                       _G2L_LOOP(g2l, item, (TREE_ARITY-1), -)
#define G2L_LOOP_END     } }

#define G2L_FIND(g2l, addr1, result, goto_not_found)            \
{                                                               \
  unsigned long _key = (unsigned long)(addr1);                  \
  char *_p = (char *)((g2l).toplevel.items);                    \
  char *_entry = *(char **)(_p + (_key & TREE_MASK));           \
  if (__builtin_expect(_entry == NULL, 1))                      \
    goto_not_found;    /* common case, hopefully */             \
  result = _g2l_find(_entry, addr1);                            \
  if (result == NULL || result->addr != (addr1))                \
    goto_not_found;                                             \
}

static wlog_t *_g2l_find(char *entry, gcptr addr)
{
  unsigned long key = (unsigned long)addr;
  while (((long)entry) & 1)
    {   /* points to a further level */
      key >>= TREE_BITS;
      entry = *(char **)((entry - 1) + (key & TREE_MASK));
    }
  return (wlog_t *)entry;   /* may be NULL */
}

static void g2l_insert(struct G2L *g2l, gcptr addr, gcptr val);

static void _g2l_grow(struct G2L *g2l, long extra)
{
  struct G2L newg2l;
  wlog_t *item;
  long alloc = g2l->raw_end - g2l->raw_start;
  long newalloc = (alloc + extra + (alloc >> 2) + 31) & ~15;
  //fprintf(stderr, "growth: %ld\n", newalloc);
  char *newitems = malloc(newalloc);
  newg2l.raw_start = newitems;
  newg2l.raw_current = newitems;
  newg2l.raw_end = newitems + newalloc;
  _g2l_clear_node(&newg2l.toplevel);
  G2L_LOOP_FORWARD(*g2l, item)
    {
      g2l_insert(&newg2l, item->addr, item->val);
    } G2L_LOOP_END;
  free(g2l->raw_start);
  *g2l = newg2l;
}

static char *_g2l_grab(struct G2L *g2l, long size)
{
  char *result;
  result = g2l->raw_current;
  g2l->raw_current += size;
  if (g2l->raw_current > g2l->raw_end)
    {
      _g2l_grow(g2l, size);
      return NULL;
    }
  return result;
}

static void g2l_insert(struct G2L *g2l, gcptr addr, gcptr val)
{
 retry:;
  wlog_t *wlog;
  unsigned long key = (unsigned long)addr;
  int shift = 0;
  char *p = (char *)(g2l->toplevel.items);
  char *entry;
  assert((key & (sizeof(void*)-1)) == 0);   /* only for aligned keys */
  while (1)
    {
      p += (key >> shift) & TREE_MASK;
      shift += TREE_BITS;
      entry = *(char **)p;
      if (entry == NULL)
        break;
      else if (((long)entry) & 1)
        {   /* points to a further level */
          p = entry - 1;
        }
      else
        {
          wlog_t *wlog1 = (wlog_t *)entry;
          /* the key must not already be present */
          assert(wlog1->addr != addr);
          /* collision: there is already a different wlog here */
          wlog_node_t *node = (wlog_node_t *)
                _g2l_grab(g2l, sizeof(wlog_node_t));
          if (node == NULL) goto retry;
          _g2l_clear_node(node);
          unsigned long key1 = (unsigned long)(wlog1->addr);
          char *p1 = (char *)(node->items);
          *(wlog_t **)(p1 + ((key1 >> shift) & TREE_MASK)) = wlog1;
          *(char **)p = ((char *)node) + 1;
          p = p1;
        }
    }
  wlog = (wlog_t *)_g2l_grab(g2l, sizeof(wlog_t));
  if (wlog == NULL) goto retry;
  wlog->addr = addr;
  wlog->val = val;
  *(char **)p = (char *)wlog;
}

/************************************************************/

/* The gcptrlist_xx functions are implemented as an array that grows
   as needed. */

struct GcPtrList {
  long size, alloc;
  gcptr *items;
};

static void gcptrlist_clear(struct GcPtrList *gcptrlist)
{
  gcptrlist->size = 0;
}

static void _gcptrlist_grow(struct GcPtrList *gcptrlist)
{
  long newalloc = gcptrlist->alloc + (gcptrlist->alloc >> 1) + 16;

  PYPY_DEBUG_START("stm-growth");
  if (PYPY_HAVE_DEBUG_PRINTS)
    {
      fprintf(PYPY_DEBUG_FILE, "%ld KB\n", newalloc * sizeof(gcptr) / 1024);
    }

  gcptr *newitems = malloc(newalloc * sizeof(gcptr));
  long i;
  for (i=0; i<gcptrlist->size; i++)
    newitems[i] = gcptrlist->items[i];
  free(gcptrlist->items);
  gcptrlist->items = newitems;
  gcptrlist->alloc = newalloc;

  PYPY_DEBUG_STOP("stm-growth");
}

static inline void gcptrlist_insert(struct GcPtrList *gcptrlist, gcptr newitem)
{
  if (__builtin_expect(gcptrlist->size == gcptrlist->alloc, 0))
    _gcptrlist_grow(gcptrlist);
  gcptrlist->items[gcptrlist->size++] = newitem;
}

static void gcptrlist_insert2(struct GcPtrList *gcptrlist, gcptr newitem1,
                              gcptr newitem2)
{
  gcptr *items;
  long i = gcptrlist->size;
  if (__builtin_expect((gcptrlist->alloc - i) < 2, 0))
    _gcptrlist_grow(gcptrlist);
  items = gcptrlist->items;
  items[i+0] = newitem1;
  items[i+1] = newitem2;
  gcptrlist->size = i + 2;
}

/************************************************************/

/* The fxcache_xx functions implement a fixed-size set of gcptr's.
   Moreover the gcptr's in the set are mapped to small integers.  In case
   of collisions, old items are discarded.  The eviction logic is a bit
   too simple for now. */

#define FX_ENTRIES    8192
#define FX_ASSOC      1
#define FX_SIZE       (FX_ENTRIES * FX_ASSOC * sizeof(revision_t))

struct FXCache {
  char *cache_start;
#if FX_ASSOC > 1
  revision_t nextadd;
#endif
  revision_t shift;
  revision_t cache[FX_ENTRIES * FX_ASSOC * 2];
};

static void fxcache_clear(struct FXCache *fxcache)
{
  fxcache->shift += FX_ASSOC;
  if (fxcache->shift > (FX_ENTRIES - 1) * FX_ASSOC) {
    memset(fxcache->cache, 0, 2 * FX_SIZE);
    fxcache->shift = 0;
  }
  fxcache->cache_start = (char *)(fxcache->cache + fxcache->shift);
}

static inline int fxcache_add(struct FXCache *fxcache, gcptr item)
{
  /* If 'item' is not in the cache, add it and returns 0.
     If it is already, return 1.
     */
  revision_t uitem = (revision_t)item;
  revision_t *entry = (revision_t *)
    (fxcache->cache_start + (uitem & (FX_SIZE-sizeof(revision_t))));

  if (entry[0] == uitem
#if FX_ASSOC >= 2
      || entry[1] == uitem
#if FX_ASSOC >= 4
      || entry[2] == uitem || entry[3] == uitem
#if FX_ASSOC >= 8
      || entry[4] == uitem || entry[5] == uitem
      || entry[6] == uitem || entry[7] == uitem
#if FX_ASSOC >= 16
      || entry[8] == uitem || entry[9] == uitem
      || entry[10]== uitem || entry[11]== uitem
      || entry[12]== uitem || entry[13]== uitem
      || entry[14]== uitem || entry[15]== uitem
#if FX_ASSOC >= 32
#error "FX_ASSOC is too large"
#endif /* 32 */
#endif /* 16 */
#endif /* 8 */
#endif /* 4 */
#endif /* 2 */
      )
    return 1;

#if FX_ASSOC > 1
  entry[fxcache->nextadd] = uitem;
  fxcache->nextadd = (fxcache->nextadd + 1) & (FX_ASSOC-1);
#else
  entry[0] = uitem;
#endif
  return 0;
}

/************************************************************/
