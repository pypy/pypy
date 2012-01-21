#include <stdlib.h>
#include <assert.h>
#include <libitm.h>


static void stm_descriptor_init(void) { /* nothing */ }
static void stm_descriptor_done(void) { /* nothing */ }

static void* stm_perform_transaction(void*(*f)(void*), void* arg)
{
    void *result;
    int _i = _ITM_beginTransaction(pr_instrumentedCode);
    assert(_i & a_runInstrumentedCode);
    /**/
    result = f(arg);
    /**/
    _ITM_commitTransaction();
    return result;
}

#define STM_CCHARP1(arg)    void
#define STM_EXPLAIN1(info)  /* nothing */

static void stm_try_inevitable(STM_CCHARP1(why))
{
    _ITM_changeTransactionMode(modeSerialIrrevocable);
}

static void stm_abort_and_retry(void)
{
    abort();   /* XXX */
}

static long stm_debug_get_state(void)
{
    return _ITM_inTransaction();
}


#if PYPY_LONG_BIT == 32
#  define stm_read_word(addr)        _ITM_RU4(addr)
#  define stm_write_word(addr, val)  _ITM_WU4(addr, val)
#else
#  define stm_read_word(addr)        _ITM_RU8(addr)
#  define stm_write_word(addr, val)  _ITM_WU8(addr, val)
#endif

// XXX little-endian only!
/* this macro is used if 'base' is a word-aligned pointer and 'offset'
   is a compile-time constant */
#define stm_fx_read_partial(base, offset)                               \
       (stm_read_word(                                                  \
           (long*)(((char*)(base)) + ((offset) & ~(sizeof(void*)-1))))  \
        >> (8 * ((offset) & (sizeof(void*)-1))))

#define stm_read_partial_1(addr)          _ITM_RU1(addr)
#define stm_read_partial_2(addr)          _ITM_RU2(addr)
#define stm_write_partial_1(addr, nval)   _ITM_WU1(addr, nval)
#define stm_write_partial_2(addr, nval)   _ITM_WU2(addr, nval)
#if PYPY_LONG_BIT == 64
#define stm_read_partial_4(addr)          _ITM_RU4(addr)
#define stm_write_partial_4(addr, nval)   _ITM_WU4(addr, nval)
#endif

#define stm_read_double(addr)             _ITM_RD(addr)
#define stm_write_double(addr, val)       _ITM_WD(addr, val)

#define stm_read_float(addr)              _ITM_RF(addr)
#define stm_write_float(addr, val)        _ITM_WF(addr, val)

#if PYPY_LONG_BIT == 32
#define stm_read_doubleword(addr)         _ITM_RU8(addr)
#define stm_write_doubleword(addr, val)   _ITM_WU8(addr, val)
#endif
