#include "weakref.h"

#include <assert.h>

#include "bag.h"
#include "gc_state.h"
#include "hugeblocktable.h"

void qcgc_register_weakref(object_t *weakrefobj, object_t **target) {
#if CHECKED
	assert((weakrefobj->flags & QCGC_PREBUILT_OBJECT) == 0);
	assert((object_t *) qcgc_arena_addr((cell_t *) weakrefobj) != weakrefobj);
#endif
	// NOTE: At this point, the target must point to a pointer to a valid
	// object. We don't register any weakrefs to prebuilt objects as they
	// are always valid.
	if (((*target)->flags & QCGC_PREBUILT_OBJECT) == 0) {
		qcgc_state.weakrefs = qcgc_weakref_bag_add(qcgc_state.weakrefs,
				(struct weakref_bag_item_s) {
					.weakrefobj = weakrefobj,
					.target = target});
	}
}

QCGC_STATIC void update_weakrefs(void) {
	size_t i = 0;
	while (i < qcgc_state.weakrefs->count) {
		struct weakref_bag_item_s item = qcgc_state.weakrefs->items[i];
		// Check whether weakref object itself was collected
		// We know the weakref object is a normal object
		switch(qcgc_arena_get_blocktype((cell_t *) item.weakrefobj)) {
			case BLOCK_EXTENT: // Fall through
			case BLOCK_FREE:
				// Weakref itself was collected, forget it
				qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
						qcgc_state.weakrefs, i);
				continue;
			case BLOCK_BLACK:
			case BLOCK_WHITE:
				// Weakref object is still valid, continue
				break;
		}

		// Check whether the weakref target is still valid
		object_t *points_to = *item.target;
		if ((object_t *) qcgc_arena_addr((cell_t *) points_to) ==
				points_to) {
			// Huge object
			if (qcgc_hbtable_has(points_to)) {
				// Still valid
				i++;
			} else {
				// Invalid
				*(item.target) = NULL;
				qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
						qcgc_state.weakrefs, i);
			}
		} else {
			// Normal object
			switch(qcgc_arena_get_blocktype((cell_t *) points_to)) {
				case BLOCK_BLACK: // Still valid
				case BLOCK_WHITE:
					i++;
					break;
				case BLOCK_EXTENT: // Fall through
				case BLOCK_FREE:
					// Invalid
					*(item.target) = NULL;
					qcgc_state.weakrefs = qcgc_weakref_bag_remove_index(
							qcgc_state.weakrefs, i);
					break;
			}
		}
	}
}
