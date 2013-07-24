/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_WEAKREF_H
#define _SRCSTM_WEAKREF_H


void stm_move_young_weakrefs(struct tx_descriptor *);
void stm_visit_old_weakrefs(void);
void stm_clean_old_weakrefs(void);


#endif
