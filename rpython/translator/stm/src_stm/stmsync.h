/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_STMSYNC_H
#define _SRCSTM_STMSYNC_H

void stm_set_max_aborts(int max_aborts);

void stm_start_sharedlock(void);
void stm_stop_sharedlock(void);

void stm_stop_all_other_threads(void);
void stm_partial_commit_and_resume_other_threads(void);
void stm_start_single_thread(void);
void stm_stop_single_thread(void);

void stm_possible_safe_point(void);

extern struct tx_descriptor *in_single_thread;
extern struct GcPtrList stm_prebuilt_gcroots;
void stm_add_prebuilt_root(gcptr);
void stm_clear_between_tests(void);

#endif
