/* -*- c-basic-offset: 2 -*- */

#include <limits.h>

/************************************************************/

/* The redolog_xx functions are implemented as a tree, supporting
   very high performance in REDOLOG_FIND in the common case where
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
  long* addr;
  long val;
  owner_version_t p;   // the previous version number (if locked)
} wlog_t;

typedef struct {
  char *items[TREE_ARITY];
} wlog_node_t;

struct RedoLog {
  char *raw_start, *raw_current, *raw_end;
  wlog_node_t toplevel;
};

static void _redolog_clear_node(wlog_node_t *node)
{
  memset(node, 0, sizeof(wlog_node_t));
}

static void redolog_clear(struct RedoLog *redolog)
{
  if (redolog->raw_current != redolog->raw_start)
    {
      _redolog_clear_node(&redolog->toplevel);
      redolog->raw_current = redolog->raw_start;
    }
}

static int redolog_any_entry(struct RedoLog *redolog)
{
  return redolog->raw_current != redolog->raw_start;
}

#define _REDOLOG_LOOP(redolog, item, INITIAL, _PLUS_)                   \
{                                                                       \
  struct { char **next; char **end; } _stack[TREE_DEPTH_MAX], *_stackp; \
  char **_next, **_end, *_entry;                                        \
  /* initialization */                                                  \
  _stackp = _stack;      /* empty stack */                              \
  _next = (redolog).toplevel.items + INITIAL;                           \
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

#define REDOLOG_LOOP_FORWARD(redolog, item)                             \
                       _REDOLOG_LOOP(redolog, item, 0, +)
#define REDOLOG_LOOP_BACKWARD(redolog, item)                            \
                       _REDOLOG_LOOP(redolog, item, (TREE_ARITY-1), -)
#define REDOLOG_LOOP_END     } }

#define REDOLOG_FIND(redolog, addr1, result, goto_not_found)    \
{                                                               \
  unsigned long _key = (unsigned long)(addr1);                  \
  char *_p = (char *)((redolog).toplevel.items);                \
  char *_entry = *(char **)(_p + (_key & TREE_MASK));           \
  if (__builtin_expect(_entry == NULL, 1))                      \
    goto_not_found;    /* common case, hopefully */             \
  result = _redolog_find(_entry, addr1);                        \
  if (result == NULL || result->addr != (addr1))                \
    goto_not_found;                                             \
}

static wlog_t *_redolog_find(char *entry, long* addr)
{
  unsigned long key = (unsigned long)addr;
  while (((long)entry) & 1)
    {   /* points to a further level */
      key >>= TREE_BITS;
      entry = *(char **)((entry - 1) + (key & TREE_MASK));
    }
  return (wlog_t *)entry;   /* may be NULL */
}

static void redolog_insert(struct RedoLog *redolog, long* addr, long val);

static void _redolog_grow(struct RedoLog *redolog, long extra)
{
  struct RedoLog newredolog;
  wlog_t *item, *newitem;
  long alloc = redolog->raw_end - redolog->raw_start;
  long newalloc = (alloc + extra + (alloc >> 2) + 31) & ~15;
  //fprintf(stderr, "growth: %ld\n", newalloc);
  char *newitems = malloc(newalloc);
  newredolog.raw_start = newitems;
  newredolog.raw_current = newitems;
  newredolog.raw_end = newitems + newalloc;
  _redolog_clear_node(&newredolog.toplevel);
  REDOLOG_LOOP_FORWARD(*redolog, item)
    {
      assert(item->p == -1);
      redolog_insert(&newredolog, item->addr, item->val);
    } REDOLOG_LOOP_END;
  free(redolog->raw_start);
  *redolog = newredolog;
}

static char *_redolog_grab(struct RedoLog *redolog, long size)
{
  char *result;
  result = redolog->raw_current;
  redolog->raw_current += size;
  if (redolog->raw_current > redolog->raw_end)
    {
      _redolog_grow(redolog, size);
      return NULL;
    }
  return result;
}

static void redolog_insert(struct RedoLog *redolog, long* addr, long val)
{
 retry:;
  wlog_t *wlog;
  unsigned long key = (unsigned long)addr;
  int shift = 0;
  char *p = (char *)(redolog->toplevel.items);
  char *entry;
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
          if (wlog1->addr == addr)
            {
              /* overwrite and that's it */
              wlog1->val = val;
              return;
            }
          /* collision: there is already a different wlog here */
          wlog_node_t *node = (wlog_node_t *)
                _redolog_grab(redolog, sizeof(wlog_node_t));
          if (node == NULL) goto retry;
          _redolog_clear_node(node);
          unsigned long key1 = (unsigned long)(wlog1->addr);
          char *p1 = (char *)(node->items);
          *(wlog_t **)(p1 + ((key1 >> shift) & TREE_MASK)) = wlog1;
          *(char **)p = ((char *)node) + 1;
          p = p1;
        }
    }
  wlog = (wlog_t *)_redolog_grab(redolog, sizeof(wlog_t));
  if (wlog == NULL) goto retry;
  wlog->addr = addr;
  wlog->val = val;
  wlog->p = -1;
  *(char **)p = (char *)wlog;
}

/************************************************************/

/* The oreclist_xx functions are implemented as an array that grows
   as needed. */

struct OrecList {
  long size, alloc;
  unsigned long locked;
  orec_t **items;
};

static void _oreclist_grow(struct OrecList *oreclist)
{
  long newalloc = oreclist->alloc + (oreclist->alloc >> 1) + 16;
  orec_t **newitems = malloc(newalloc * sizeof(orec_t *));
  long i;
  for (i=0; i<oreclist->size; i++)
    newitems[i] = oreclist->items[i];
  while (!bool_cas(&oreclist->locked, 0, 1))
    /* rare case */ ;
  free(oreclist->items);
  oreclist->items = newitems;
  oreclist->alloc = newalloc;
  CFENCE;
  oreclist->locked = 0;
}

static void oreclist_insert(struct OrecList *oreclist, orec_t *newitem)
{
  if (oreclist->size == oreclist->alloc)
    _oreclist_grow(oreclist);
  oreclist->items[oreclist->size++] = newitem;
}

/************************************************************/
