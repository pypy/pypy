/* Imported by rpython/translator/stm/import_stmgc.py: 45380d4cb89c */
#ifndef _SRCSTM_DBGMEM_H
#define _SRCSTM_DBGMEM_H


#ifdef _GC_DEBUG

void *stm_malloc(size_t);
void stm_free(void *, size_t);
int _stm_can_access_memory(char *);

#else

#define stm_malloc(sz)    malloc(sz)
#define stm_free(p,sz)    free(p)

#endif

void stm_clear_large_memory_chunk(void *, size_t, size_t);


#endif
