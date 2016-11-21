/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

#define LIST_SETSIZE(n)    (sizeof(struct list_s) + LIST_ITEMSSIZE(n))
#define LIST_ITEMSSIZE(n)  ((n) * sizeof(uintptr_t))
#define LIST_OVERCNT(n)    (33 + ((((n) / 2) * 3) | 1))

static struct list_s *list_create(void)
{
    uintptr_t initial_allocation = 32;
    struct list_s *lst = malloc(LIST_SETSIZE(initial_allocation));
    if (lst == NULL)
        stm_fatalerror("out of memory in list_create");   /* XXX */

    lst->count = 0;
    lst->last_allocated = initial_allocation - 1;
    return lst;
}

static struct list_s *_list_grow(struct list_s *lst, uintptr_t nalloc)
{
    nalloc = LIST_OVERCNT(nalloc);
    lst = realloc(lst, LIST_SETSIZE(nalloc));
    if (lst == NULL)
        stm_fatalerror("out of memory in _list_grow");   /* XXX */

    lst->last_allocated = nalloc - 1;
    return lst;
}

static struct list_s *list_extend(struct list_s *lst, struct list_s *lst2,
                                  uintptr_t slicestart)
{
    if (lst2->count <= slicestart)
        return lst;
    uintptr_t baseindex = lst->count;
    lst->count = baseindex + lst2->count - slicestart;
    uintptr_t lastindex = lst->count - 1;
    if (lastindex > lst->last_allocated)
        lst = _list_grow(lst, lastindex);
    memcpy(lst->items + baseindex, lst2->items + slicestart,
           (lst2->count - slicestart) * sizeof(uintptr_t));
    return lst;
}


/************************************************************/

static void _tree_clear_node(wlog_node_t *node)
{
    memset(node, 0, sizeof(wlog_node_t));
}

static void tree_clear(struct tree_s *tree)
{
    if (tree->raw_current != tree->raw_start) {
        _tree_clear_node(&tree->toplevel);
        tree->raw_current = tree->raw_start;
        tree->count = 0;
    }
    assert(tree->count == 0);
}

static struct tree_s *tree_create(void)
{
    return (struct tree_s *)calloc(1, sizeof(struct tree_s));
}

static void tree_free(struct tree_s *tree)
{
    free(tree->raw_start);
    assert(memset(tree, 0xDD, sizeof(struct tree_s)));
    free(tree);
}

static void _tree_compress(struct tree_s *tree)
{
    wlog_t *item;
    struct tree_s tree_copy;
    memset(&tree_copy, 0, sizeof(struct tree_s));

    TREE_LOOP_FORWARD(tree, item) {
        tree_insert(&tree_copy, item->addr, item->val);

    } TREE_LOOP_END;

    free(tree->raw_start);
    *tree = tree_copy;
}

static wlog_t *_tree_find(char *entry, uintptr_t addr)
{
    uintptr_t key = TREE_HASH(addr);
    while (((long)entry) & 1) {
        /* points to a further level */
        key >>= TREE_BITS;
        entry = *(char **)((entry - 1) + (key & TREE_MASK));
    }
    return (wlog_t *)entry;   /* may be NULL */
}

static void _tree_grow(struct tree_s *tree, long extra)
{
    struct tree_s newtree;
    wlog_t *item;
    long alloc = tree->raw_end - tree->raw_start;
    long newalloc = (alloc + extra + (alloc >> 2) + 31) & ~15;
    //fprintf(stderr, "growth: %ld\n", newalloc);
    char *newitems = malloc(newalloc);
    if (newitems == NULL) {
        stm_fatalerror("out of memory!");   /* XXX */
    }
    newtree.raw_start = newitems;
    newtree.raw_current = newitems;
    newtree.raw_end = newitems + newalloc;
    newtree.count = 0;
    _tree_clear_node(&newtree.toplevel);
    TREE_LOOP_FORWARD(tree, item)
    {
        tree_insert(&newtree, item->addr, item->val);
    } TREE_LOOP_END;
    free(tree->raw_start);
    *tree = newtree;
}

static char *_tree_grab(struct tree_s *tree, long size)
{
    char *result;
    result = tree->raw_current;
    tree->raw_current += size;
    if (tree->raw_current > tree->raw_end) {
        _tree_grow(tree, size);
        return NULL;
    }
    return result;
}

static void tree_insert(struct tree_s *tree, uintptr_t addr, uintptr_t val)
{
    assert(addr != 0);    /* the NULL key is reserved */
 retry:;
    wlog_t *wlog;
    uintptr_t key = TREE_HASH(addr);
    int shift = 0;
    char *p = (char *)(tree->toplevel.items);
    char *entry;
    while (1) {
        assert(shift < TREE_DEPTH_MAX * TREE_BITS);
        p += (key >> shift) & TREE_MASK;
        shift += TREE_BITS;
        entry = *(char **)p;
        if (entry == NULL)
            break;
        else if (((long)entry) & 1) {
            /* points to a further level */
            p = entry - 1;
        }
        else {
            wlog_t *wlog1 = (wlog_t *)entry;
            if (wlog1->addr == 0) {
                /* reuse the deleted entry and that's it */
                wlog1->addr = addr;
                wlog1->val = val;
                (tree->count)++;
                return;
            }
            /* the key must not already be present */
            assert(wlog1->addr != addr);
            /* collision: there is already a different wlog here */
            wlog_node_t *node = (wlog_node_t *)
                _tree_grab(tree, sizeof(wlog_node_t));
            if (node == NULL) goto retry;
            _tree_clear_node(node);
            uintptr_t key1 = TREE_HASH(wlog1->addr);
            char *p1 = (char *)(node->items);
            *(wlog_t **)(p1 + ((key1 >> shift) & TREE_MASK)) = wlog1;
            *(char **)p = ((char *)node) + 1;
            p = p1;
        }
    }
    wlog = (wlog_t *)_tree_grab(tree, sizeof(wlog_t));
    if (wlog == NULL) goto retry;
    wlog->addr = addr;
    wlog->val = val;
    *(char **)p = (char *)wlog;
    (tree->count)++;
}

static bool tree_delete_item(struct tree_s *tree, uintptr_t addr)
{
    wlog_t *entry;
    TREE_FIND(tree, addr, entry, goto missing);
    entry->addr = 0;
    tree->count--;
    return true;

 missing:
    return false;
}

static wlog_t *tree_item(struct tree_s *tree, int index)
{
    int i = 0;
    wlog_t *item;
    TREE_LOOP_FORWARD(tree, item);
    if (i == index)
        return item;
    i++;
    TREE_LOOP_END;
    return NULL;
}
