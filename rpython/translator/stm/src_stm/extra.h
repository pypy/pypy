/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_EXTRA_H
#define _SRCSTM_EXTRA_H


struct tx_abort_info {
    char signature_packed;  /* 127 when the abort_info is in this format */
    long long elapsed_time;
    int abort_reason;
    int active;
    long atomic;
    unsigned long count_reads;
    unsigned long reads_size_limit_nonatomic;
    revision_t words[1];    /* the 'words' list is a bytecode-like format */
};

void stm_copy_to_old_id_copy(gcptr obj, gcptr id);
size_t stm_decode_abort_info(struct tx_descriptor *d, long long elapsed_time,
                             int abort_reason, struct tx_abort_info *output);
void stm_visit_abort_info(struct tx_descriptor *d, void (*visit)(gcptr *));

#endif
