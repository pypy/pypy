#include "bag.h"

#include <assert.h>

DEFINE_BAG(arena_bag, arena_t *);
DEFINE_BAG(linear_free_list, cell_t *);
DEFINE_BAG(exp_free_list, struct exp_free_list_item_s);
