/* Imported by rpython/translator/stm/import_stmgc.py */
#define NUM_BUCKETS  93

static struct list_s *debug_seen_buckets[NUM_BUCKETS];

static bool debug_add_seen(object_t *obj)
{
    long n = ((uintptr_t)obj) % NUM_BUCKETS;
    struct list_s *lst = debug_seen_buckets[n];
    long i;
    for (i = list_count(lst); i--; )
        if (list_item(lst, i) == (uintptr_t)obj)
            return false;
    LIST_APPEND(debug_seen_buckets[n], obj);
    return true;
}
