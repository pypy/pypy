#include <string.h>

RPY_EXTERN void rpy_reverse_db_setup(int argc, char *argv[]);
RPY_EXTERN void rpy_reverse_db_flush(void);


RPY_EXTERN Signed *rpy_rev_buf_p, *rpy_rev_buf_end;


static inline void rpy_reverse_db_emit(Signed value) {
    *(rpy_rev_buf_p++) = value;
    if (rpy_rev_buf_p == rpy_rev_buf_end)
        rpy_reverse_db_flush();
}

static inline void rpy_reverse_db_emit_float(double value) {
    /* xxx for 'long double' this can loose some precision */
    Signed sval[sizeof(double) / SIZEOF_LONG];
    memcpy(sval, &value, sizeof(value));
    rpy_reverse_db_emit(sval[0]);
    if (SIZEOF_LONG < sizeof(double))  /* assume len(sval) is exactly 1 or 2 */
        rpy_reverse_db_emit(sval[1]);
}

static inline void rpy_reverse_db_emit_two_longs(long long value)
{
    Signed sval[2];
    assert(SIZEOF_LONG * 2 == SIZEOF_LONG_LONG);
    memcpy(sval, &value, sizeof(value));
    rpy_reverse_db_emit(sval[0]);
    rpy_reverse_db_emit(sval[1]);
}
