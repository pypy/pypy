#include <stdlib.h>
#if defined _MSC_VER
 #if _MSC_VER < 1600
  #include <intrin.h>
  int __sync_lock_test_and_set(int * i, int j)
  {
    return _interlockedbittestandreset(i, j);
  }
  int __sync_lock_release(int *i)
  {
    return _interlockedbittestandreset(i, 0);
  }
  #ifdef _WIN32
   typedef unsigned int uintptr_t;
  #else
   typedef usigned long uintptr_t;
  #endif
 #endif
#else
#include <stdint.h>
#endif


#define HAS_SKIPLIST
#define SKIPLIST_HEIGHT   8

typedef struct skipnode_s {
    uintptr_t key;
    char *data;
    struct skipnode_s *next[SKIPLIST_HEIGHT];   /* may be smaller */
} skipnode_t;

static skipnode_t *skiplist_malloc(uintptr_t datasize)
{
    char *result;
    uintptr_t basesize;
    uintptr_t length = 1;
    while (length < SKIPLIST_HEIGHT && (rand() & 3) == 0)
        length++;
    basesize = sizeof(skipnode_t) -
               (SKIPLIST_HEIGHT - length) * sizeof(skipnode_t *);
    result = malloc(basesize + datasize);
    if (result != NULL) {
        ((skipnode_t *)result)->data = result + basesize;
    }
    return (skipnode_t *)result;
}

static skipnode_t *skiplist_search(skipnode_t *head, uintptr_t searchkey)
{
    /* Returns the skipnode with key closest (but <=) searchkey.
       Note that if there is no item with key <= searchkey in the list,
       this will return the head node. */
    uintptr_t level = SKIPLIST_HEIGHT - 1;
    while (1) {
        skipnode_t *next = head->next[level];
        if (next != NULL && next->key <= searchkey) {
            head = next;
        }
        else {
            if (level == 0)
                break;
            level -= 1;
        }
    }
    return head;
}

static void skiplist_insert(skipnode_t *head, skipnode_t *new)
{
    uintptr_t size0 = sizeof(skipnode_t) -
                      SKIPLIST_HEIGHT * sizeof(skipnode_t *);
    uintptr_t height_of_new = (new->data - ((char *)new + size0)) /
                              sizeof(skipnode_t *);

    uintptr_t level = SKIPLIST_HEIGHT - 1;
    uintptr_t searchkey = new->key;
    while (1) {
        skipnode_t *next = head->next[level];
        if (next != NULL && next->key <= searchkey) {
            head = next;
        }
        else {
            if (level < height_of_new) {
                new->next[level] = next;
                head->next[level] = new;
                if (level == 0)
                    break;
            }
            level -= 1;
        }
    }
}

static skipnode_t *skiplist_remove(skipnode_t *head, uintptr_t exact_key)
{
    uintptr_t level = SKIPLIST_HEIGHT - 1;
    while (1) {
        skipnode_t *next = head->next[level];
        if (next != NULL && next->key <= exact_key) {
            if (next->key == exact_key) {
                head->next[level] = next->next[level];
                if (level == 0)
                    return next;    /* successfully removed */
                level -= 1;
            }
            else
                head = next;
        }
        else {
            if (level == 0)
                return NULL;    /* 'exact_key' not found! */
            level -= 1;
        }
    }
}

static uintptr_t skiplist_firstkey(skipnode_t *head)
{
    if (head->next[0] == NULL)
        return 0;
    return head->next[0]->key;
}
