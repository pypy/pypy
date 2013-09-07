/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_EXTRA_H
#define _SRCSTM_EXTRA_H


void stm_copy_to_old_id_copy(gcptr obj, gcptr id);
size_t stm_decode_abort_info(struct tx_descriptor *d, long long elapsed_time,
                             int abort_reason, char *output);

#endif
