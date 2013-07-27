/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_DBGMEM_H
#define _SRCSTM_DBGMEM_H


#ifdef _GC_DEBUG

void *stm_malloc(size_t);
void stm_free(void *, size_t);
void *stm_realloc(void *, size_t, size_t);
int _stm_can_access_memory(char *);
void assert_cleared(char *, size_t);

#else

#define stm_malloc(sz)    malloc(sz)
#define stm_free(p,sz)    free(p)
#define stm_realloc(p,newsz,oldsz)  realloc(p,newsz)
#define assert_cleared(p,sz)     do { } while(0)

#endif

void stm_clear_large_memory_chunk(void *, size_t, size_t);


#endif
