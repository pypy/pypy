#include "bag.h"

#include <assert.h>

DEFINE_BAG(arena_bag, arena_t *);
DEFINE_BAG(linear_free_list, cell_t *);
DEFINE_BAG(exp_free_list, struct exp_free_list_item_s);
DEFINE_BAG(hbbucket, struct hbtable_entry_s);
DEFINE_BAG(weakref_bag, struct weakref_bag_item_s);
