/**
 * @file	qcgc.h
 */

#pragma once

#include <stddef.h>

#include "src/object.h"

/**
 * Initialize the garbage collector.
 */
void qcgc_initialize(void);

/**
 * Destroy the garbage collector.
 */
void qcgc_destroy(void);

/**
 * Allocate a new object. May trigger garabge collection.
 *
 * @param	size	Object size in bytes
 * @return	Pointer to memory region large enough to hold size bytes or NULL in
 *			case of errros
 */
object_t *qcgc_allocate(size_t size);

/**
 * Push root object.
 *
 * @param	object	The root object
 */
void qcgc_push_root(object_t *object);

/**
 * Pop root object.
 */
void qcgc_pop_root(void);

/**
 * Write barrier. Has to be called whenever a reference to another object is
 * updated.
 *
 * @param	object	Object that is updated
 */
void qcgc_write(object_t *object);

/**
 * Run garbage collection.
 */
void qcgc_collect(void);

/**
 * Weakref registration.
 *
 * @param	weakrefobj	Pointer to the weakref itself
 * @param	target		Doublepointer to referenced object.
 *						The referenced object must be a valid object.
 */
void qcgc_register_weakref(object_t *weakrefobj, object_t **target);

/**
 * Tracing function.
 *
 * This used provided function has to call visit on every object the given
 * argument references.
 *
 * @param	object	The object to trace
 * @param	visit	The function to be called on the referenced objects
 */
extern void qcgc_trace_cb(object_t *object, void (*visit)(object_t *object));
