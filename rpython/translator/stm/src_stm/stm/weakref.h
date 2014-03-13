/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_WEAKREF_H
#define _SRCSTM_WEAKREF_H

object_t *stm_allocate_weakref(ssize_t size_rounded_up);
static void stm_move_young_weakrefs(void);
static void stm_visit_old_weakrefs(void);


#endif
