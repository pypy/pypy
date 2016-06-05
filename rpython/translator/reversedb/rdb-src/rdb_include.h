

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
    Signed sval[8 / SIZEOF_LONG];
    assert(sizeof(double) == 8);
    memcpy(sval, &value, sizeof(value));
    rpy_reverse_db_emit(sval[0]);
    if (SIZEOF_LONG <= 4)
        rpy_reverse_db_emit(sval[1]);
}
