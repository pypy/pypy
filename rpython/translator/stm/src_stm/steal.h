/* Imported by rpython/translator/stm/import_stmgc.py: 45380d4cb89c */
#ifndef _SRCSTM_STEAL_H
#define _SRCSTM_STEAL_H


struct stm_stub_s {
    struct stm_object_s s_header;
    struct tx_public_descriptor *s_thread;
};

#define STUB_THREAD(h)    (((struct stm_stub_s *)(h))->s_thread)

gcptr stm_stub_malloc(struct tx_public_descriptor *);
void stm_steal_stub(gcptr);
gcptr stm_get_stolen_obj(long index);   /* debugging */
void stm_normalize_stolen_objects(struct tx_descriptor *);
gcptr _stm_find_stolen_objects(struct tx_descriptor *, gcptr);


#endif
