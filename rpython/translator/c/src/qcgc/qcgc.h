/**
 * @file	qcgc.h
 */

#pragma once

#include "config.h"

#include <stdint.h>
#include <sys/types.h>

#include "arena.h"
#include "gc_state.h"
#include "gray_stack.h"
#include "object.h"

/**
 * @typedef mark_color
 * Object state during collection
 * - MARK_COLOR_WHITE		Clean and unprocessed
 * - MARK_COLOR_LIGHT_GRAY	Dirty and unprocessed
 * - MARK_COLOR_DARK_GRAY	Processing
 * - MARK_COLOR_BLACK		Processed
 */
typedef enum mark_color {
	MARK_COLOR_WHITE,
	MARK_COLOR_LIGHT_GRAY,
	MARK_COLOR_DARK_GRAY,
	MARK_COLOR_BLACK,
} mark_color_t;

/**
 * Initialize the garbage collector.
 */
void qcgc_initialize(void);

/**
 * Destroy the garbage collector.
 */
void qcgc_destroy(void);

/**
 * Write barrier.
 *
 * @param	object	Object to write to
 */
void qcgc_write(object_t *object);

/**
 * Allocate new memory region
 *
 * @param	size	Desired size of the memory region
 * @return	Pointer to memory large enough to hold size bytes, NULL in case of
 *			errors
 */
object_t *qcgc_allocate(size_t size);

/**
 * Run garbage collection.
 */
void qcgc_collect(void);

/**
 * Return color of object.
 *
 * @returs The color of the object, according to the mark algorithm.
 */
mark_color_t qcgc_get_mark_color(object_t *object);

/**
 * Add object to shadow stack
 *
 * @param	object	The object to push
 */
void qcgc_shadowstack_push(object_t *object);

/**
 * Pop object from shadow stack
 *
 * @return	Top element of the shadowstack
 */
object_t *qcgc_shadowstack_pop(void);

/**
 * Tracing function.
 *
 * This function traces an object, i.e. calls visit on every object referenced
 * by the given object. Has to be provided by the library user.
 *
 * @param	object	The object to trace
 * @param	visit	The function to be called on the referenced objects
 */
extern void qcgc_trace_cb(object_t *object, void (*visit)(object_t *object));
