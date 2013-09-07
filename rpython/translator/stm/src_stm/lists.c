/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"

/************************************************************/

static void _g2l_clear_node(wlog_node_t *node)
{
  memset(node, 0, sizeof(wlog_node_t));
}

void g2l_clear(struct G2L *g2l)
{
  if (g2l->raw_current != g2l->raw_start)
    {
      _g2l_clear_node(&g2l->toplevel);
      g2l->raw_current = g2l->raw_start;
    }
}

void g2l_delete(struct G2L *g2l)
{
  stm_free(g2l->raw_start);
  memset(g2l, 0, sizeof(struct G2L));
}

void _g2l_compress(struct G2L *g2l)
{
  wlog_t *item;
  struct G2L g2l_copy;
  memset(&g2l_copy, 0, sizeof(struct G2L));

  G2L_LOOP_FORWARD(*g2l, item)
    {
      g2l_insert(&g2l_copy, item->addr, item->val);

    } G2L_LOOP_END;

  g2l_delete_not_used_any_more(g2l);
  *g2l = g2l_copy;
}

wlog_t *_g2l_find(char *entry, gcptr addr)
{
  revision_t key = (revision_t)addr;
  while (((long)entry) & 1)
    {   /* points to a further level */
      key >>= TREE_BITS;
      entry = *(char **)((entry - 1) + (key & TREE_MASK));
    }
  return (wlog_t *)entry;   /* may be NULL */
}

static void _g2l_grow(struct G2L *g2l, long extra)
{
  struct G2L newg2l;
  wlog_t *item;
  long alloc = g2l->raw_end - g2l->raw_start;
  long newalloc = (alloc + extra + (alloc >> 2) + 31) & ~15;
  //fprintf(stderr, "growth: %ld\n", newalloc);
  char *newitems = stm_malloc(newalloc);
  newg2l.raw_start = newitems;
  newg2l.raw_current = newitems;
  newg2l.raw_end = newitems + newalloc;
  _g2l_clear_node(&newg2l.toplevel);
  G2L_LOOP_FORWARD(*g2l, item)
    {
      g2l_insert(&newg2l, item->addr, item->val);
    } G2L_LOOP_END;
  stm_free(g2l->raw_start);
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

void g2l_insert(struct G2L *g2l, gcptr addr, gcptr val)
{
 retry:;
  wlog_t *wlog;
  revision_t key = (revision_t)addr;
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
          if (wlog1->addr == NULL) {
              /* reuse the deleted entry and that's it */
              wlog1->addr = addr;
              wlog1->val = val;
              return;
          }
          /* the key must not already be present */
          assert(wlog1->addr != addr);
          /* collision: there is already a different wlog here */
          wlog_node_t *node = (wlog_node_t *)
                _g2l_grab(g2l, sizeof(wlog_node_t));
          if (node == NULL) goto retry;
          _g2l_clear_node(node);
          revision_t key1 = (revision_t)(wlog1->addr);
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

int g2l_delete_item(struct G2L *g2l, gcptr addr)
{
    wlog_t *entry;
    G2L_FIND(*g2l, addr, entry, goto missing);
    entry->addr = NULL;
    return 1;

 missing:
    return 0;
}

/************************************************************/

void gcptrlist_delete(struct GcPtrList *gcptrlist)
{
    //if (gcptrlist->items)
    //fprintf(stderr, "list %p deleted (%ld KB)\n",
    //gcptrlist, gcptrlist->alloc * sizeof(gcptr) / 1024);
  gcptrlist->size = 0;
  stm_free(gcptrlist->items);
  gcptrlist->items = NULL;
  gcptrlist->alloc = 0;
}

void gcptrlist_compress(struct GcPtrList *gcptrlist)
{
  if (gcptrlist->alloc <= gcptrlist->size + 64)
    return;

  size_t nsize = gcptrlist->size * sizeof(gcptr);
  gcptr *newitems = stm_realloc(gcptrlist->items, nsize,
                                gcptrlist->alloc * sizeof(gcptr));
  if (newitems != NULL || nsize == 0)
    {
      gcptrlist->items = newitems;
      gcptrlist->alloc = gcptrlist->size;
    }
}

void _gcptrlist_grow(struct GcPtrList *gcptrlist)
{
  long newalloc = gcptrlist->alloc + (gcptrlist->alloc >> 1) + 64;

  //fprintf(stderr, "list %p growth to %ld items (%ld KB)\n",
  //          gcptrlist, newalloc, newalloc * sizeof(gcptr) / 1024);

  gcptr *newitems = stm_malloc(newalloc * sizeof(gcptr));
  long i;
  for (i=0; i<gcptrlist->size; i++)
    newitems[i] = gcptrlist->items[i];
  stm_free(gcptrlist->items);
  gcptrlist->items = newitems;
  gcptrlist->alloc = newalloc;
}

void gcptrlist_insert2(struct GcPtrList *gcptrlist, gcptr newitem1,
                       gcptr newitem2)
{
  gcptr *items;
  long i = gcptrlist->size;
  if (UNLIKELY((gcptrlist->alloc - i) < 2))
    _gcptrlist_grow(gcptrlist);
  items = gcptrlist->items;
  items[i+0] = newitem1;
  items[i+1] = newitem2;
  gcptrlist->size = i + 2;
}

void gcptrlist_insert3(struct GcPtrList *gcptrlist, gcptr newitem1,
                       gcptr newitem2, gcptr newitem3)
{
  gcptr *items;
  long i = gcptrlist->size;
  if (UNLIKELY((gcptrlist->alloc - i) < 3))
    _gcptrlist_grow(gcptrlist);
  items = gcptrlist->items;
  items[i+0] = newitem1;
  items[i+1] = newitem2;
  items[i+2] = newitem3;
  gcptrlist->size = i + 3;
}

void gcptrlist_insert_at_index(struct GcPtrList *gcptrlist, long index,
                               gcptr newitem)
{
    long lastitem = gcptrlist->size;
    assert(index <= lastitem);
    gcptrlist_insert(gcptrlist, NULL);
    gcptrlist->items[lastitem] = gcptrlist->items[index];
    gcptrlist->items[index] = newitem;
}

void gcptrlist_merge(struct GcPtrList *gcptrlist,
                     struct GcPtrList *gcptrlist_source)
{
    gcptr *items, *items_src;
    long i = gcptrlist->size, i_src = gcptrlist_source->size;
    if (i_src == 0)
        return;
    while (UNLIKELY((gcptrlist->alloc - i) < i_src))
        _gcptrlist_grow(gcptrlist);
    items = gcptrlist->items + i;
    items_src = gcptrlist_source->items;
    i += i_src;
    while (i_src > 0) {
        *items++ = *items_src++;
        i_src--;
    }
    gcptrlist->size = i;
}

void gcptrlist_move(struct GcPtrList *gcptrlist,
                    struct GcPtrList *gcptrlist_source)
{
    gcptrlist_merge(gcptrlist, gcptrlist_source);
    gcptrlist_clear(gcptrlist_source);
}

/************************************************************/

__thread char *stm_read_barrier_cache;

void _fxcache_reset(struct FXCache *fxcache)
{
    fxcache->shift = 0;
    memset(fxcache->cache, 0, sizeof(fxcache->cache));
}

/************************************************************/
