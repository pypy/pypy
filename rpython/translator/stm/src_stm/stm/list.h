/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _LIST_H
#define _LIST_H

#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>


/************************************************************/

struct list_s {
    uintptr_t count;
    uintptr_t last_allocated;
    uintptr_t items[];
};

static struct list_s *list_create(void) __attribute__((unused));

static inline void _list_free(struct list_s *lst)
{
    free(lst);
}

#define LIST_CREATE(lst)  ((lst) = list_create())
#define LIST_FREE(lst)  (_list_free(lst), (lst) = NULL)


static struct list_s *_list_grow(struct list_s *, uintptr_t);

static inline struct list_s *list_append(struct list_s *lst, uintptr_t item)
{
    uintptr_t index = lst->count++;
    if (UNLIKELY(index > lst->last_allocated))
        lst = _list_grow(lst, index);
    lst->items[index] = item;
    return lst;
}

#define LIST_APPEND(lst, e)   ((lst) = list_append((lst), (uintptr_t)(e)))

static inline struct list_s *list_append2(struct list_s *lst,
                                          uintptr_t item0, uintptr_t item1)
{
    uintptr_t index = lst->count;
    lst->count += 2;
    if (UNLIKELY(index >= lst->last_allocated))
        lst = _list_grow(lst, index + 1);
    lst->items[index + 0] = item0;
    lst->items[index + 1] = item1;
    return lst;
}

static inline struct list_s *list_append3(struct list_s *lst, uintptr_t item0,
                                          uintptr_t item1, uintptr_t item2)
{
    uintptr_t index = lst->count;
    lst->count += 3;
    if (UNLIKELY(index + 2 > lst->last_allocated))
        lst = _list_grow(lst, index + 2);
    lst->items[index + 0] = item0;
    lst->items[index + 1] = item1;
    lst->items[index + 2] = item2;
    return lst;
}


static inline void list_clear(struct list_s *lst)
{
    lst->count = 0;
}

static inline bool list_is_empty(struct list_s *lst)
{
    return (lst->count == 0);
}

static inline uintptr_t list_count(struct list_s *lst)
{
    return lst->count;
}

static inline uintptr_t list_pop_item(struct list_s *lst)
{
    assert(lst->count > 0);
    return lst->items[--lst->count];
}

static inline uintptr_t list_item(struct list_s *lst, uintptr_t index)
{
    return lst->items[index];
}

static inline void list_set_item(struct list_s *lst, uintptr_t index,
                                 uintptr_t newitem)
{
    lst->items[index] = newitem;
}

static inline uintptr_t *list_ptr_to_item(struct list_s *lst, uintptr_t index)
{
    return &lst->items[index];
}

static struct list_s *list_extend(struct list_s *lst, struct list_s *lst2,
                                  uintptr_t slicestart);


#define LIST_FOREACH_R(lst, TYPE, CODE)         \
    do {                                        \
        struct list_s *_lst = (lst);            \
        uintptr_t _i;                           \
        for (_i = _lst->count; _i--; ) {        \
            TYPE item = (TYPE)_lst->items[_i];  \
            CODE;                               \
        }                                       \
    } while (0)

/************************************************************/

/* The tree_xx functions are, like the name hints, implemented as a tree,
   supporting very high performance in TREE_FIND in the common case where
   there are no or few elements in the tree, but scaling correctly
   if the number of items becomes large (logarithmically, rather
   than almost-constant-time with hash maps, but with low constants).
   The value 0 cannot be used as a key.
*/

#define TREE_BITS   4
#define TREE_ARITY  (1 << TREE_BITS)

#define TREE_DEPTH_MAX   ((sizeof(void*)*8 + TREE_BITS-1) / TREE_BITS)
/* sizeof(void*)*8 = total number of bits
   (x + TREE_BITS-1) / TREE_BITS = divide by TREE_BITS, rounding up
*/

#define TREE_HASH(key)  ((key) ^ ((key) << 4))
#define TREE_MASK   ((TREE_ARITY - 1) * sizeof(void*))

typedef struct {
    uintptr_t addr;
    uintptr_t val;
} wlog_t;

typedef struct {
    char *items[TREE_ARITY];
} wlog_node_t;

struct tree_s {
    uintptr_t count;
    char *raw_start, *raw_current, *raw_end;
    wlog_node_t toplevel;
};

static struct tree_s *tree_create(void) __attribute__((unused));
static void tree_free(struct tree_s *tree) __attribute__((unused));
static void tree_clear(struct tree_s *tree) __attribute__((unused));
//static inline void tree_delete_not_used_any_more(struct tree_s *tree)...

static inline bool tree_is_cleared(struct tree_s *tree) {
    return tree->raw_current == tree->raw_start;
}

static inline bool tree_is_empty(struct tree_s *tree) {
    return tree->count == 0;
}

static inline uintptr_t tree_count(struct tree_s *tree) {
    assert(tree->count >= 0);
    return tree->count;
}

#define _TREE_LOOP(tree, item, INITIAL, _PLUS_)                         \
{                                                                       \
  struct { char **next; char **end; } _stack[TREE_DEPTH_MAX], *_stackp; \
  char **_next, **_end, *_entry;                                        \
  long _deleted_factor = 0;                                             \
  struct tree_s *_tree = (tree);                                       \
  /* initialization */                                                  \
  _stackp = _stack;      /* empty stack */                              \
  _next = _tree->toplevel.items + INITIAL;                              \
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
          assert(_stackp - _stack < TREE_DEPTH_MAX);                    \
          _stackp->next = _next;                                        \
          _stackp->end = _end;                                          \
          _stackp++;                                                    \
          _next = ((wlog_node_t *)(_entry - 1))->items + INITIAL;       \
          _end = _next _PLUS_ TREE_ARITY;                               \
          continue;                                                     \
        }                                                               \
      /* points to a wlog_t item */                                     \
      if (((wlog_t *)_entry)->addr == 0) {      /* deleted entry */     \
          _deleted_factor += 3;                                         \
          continue;                                                     \
      }                                                                 \
      _deleted_factor -= 4;                                             \
      item = (wlog_t *)_entry;

#define TREE_LOOP_FORWARD(tree, item)                             \
                       _TREE_LOOP(tree, item, 0, +)
#define TREE_LOOP_BACKWARD(tree, item)                            \
                       _TREE_LOOP(tree, item, (TREE_ARITY-1), -)
#define TREE_LOOP_END     } }
#define TREE_LOOP_END_AND_COMPRESS                                       \
                         } if (_deleted_factor > 9) _tree_compress(_tree); }
#define TREE_LOOP_DELETE(tree, item)  { (tree)->count--; (item)->addr = 0; _deleted_factor += 6; }
#define TREE_FIND_DELETE(tree, item)  { (tree)->count--; (item)->addr = 0; }


#define TREE_FIND(tree, addr1, result, goto_not_found)          \
{                                                               \
  uintptr_t _key = TREE_HASH(addr1);                            \
  char *_p = (char *)((tree)->toplevel.items);                   \
  char *_entry = *(char **)(_p + (_key & TREE_MASK));           \
  if (_entry == NULL)                                           \
    goto_not_found;    /* common case, hopefully */             \
  result = _tree_find(_entry, addr1);                           \
  if (result == NULL || result->addr != (addr1))                \
    goto_not_found;                                             \
}

static wlog_t *_tree_find(char *entry, uintptr_t addr);
static void _tree_compress(struct tree_s *tree) __attribute__((unused));
static void tree_insert(struct tree_s *tree, uintptr_t addr, uintptr_t val);
static bool tree_delete_item(struct tree_s *tree, uintptr_t addr)
     __attribute__((unused));
static wlog_t *tree_item(struct tree_s *tree, int index) __attribute__((unused)); /* SLOW */

static inline bool tree_contains(struct tree_s *tree, uintptr_t addr)
{
    wlog_t *result;
    TREE_FIND(tree, addr, result, return false);
    return true;
}

#endif
