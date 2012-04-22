
#define PYPY_LONG_BIT   (sizeof(long) * 8)

struct pypy_header0 {
    long h_tid;
    void *h_version;
};

struct pypy_pypy_rlib_rstm_Transaction0 {
    struct pypy_header0 header;
    struct pypy_pypy_rlib_rstm_Transaction0 *t_inst__next_transaction;
    int foobar;
    void (*callback)(void);
};

typedef char bool_t;


#include "src_stm/et.h"
#include "src_stm/et.c"


void *(*cb_run_transaction)(void *, long);
long (*cb_getsize)(void *);
void (*cb_enum_callback)(void *, void *, void *);

int _thread_started = 0;


void pypy_g__stm_thread_starting(void) {
    assert(_thread_started == 0);
    _thread_started = 1;
    stm_set_tls((void *)742, 0);
}
void pypy_g__stm_thread_stopping(void) {
    assert(_thread_started == 1);
    _thread_started = 0;
    stm_del_tls();
}
void *pypy_g__stm_run_transaction(void *a, long b) {
    assert(cb_run_transaction != NULL);
    return cb_run_transaction(a, b);
}
long pypy_g__stm_getsize(void *a) {
    assert(cb_getsize != NULL);
    return cb_getsize(a);
}
void pypy_g__stm_enum_callback(void *a, void *b, void *c) {
    assert(cb_enum_callback != NULL);
    cb_enum_callback(a, b, c);
}


void test_set_get_del(void)
{
    stm_set_tls((void *)42, 1);
    assert(stm_get_tls() == (void *)42);
    stm_del_tls();
}

void *rt1(void *t1, long retry_counter)
{
    struct pypy_pypy_rlib_rstm_Transaction0 *t = t1;
    assert(retry_counter == 0);
    assert(t->foobar == 42);
    t->foobar = 143;
    return NULL;
}
void test_run_all_transactions(void)
{
    struct pypy_pypy_rlib_rstm_Transaction0 t;
    t.foobar = 42;
    cb_run_transaction = rt1;
    stm_run_all_transactions(&t, 1);
    assert(t.foobar == 143);
}

void *rt2(void *t1, long retry_counter)
{
    struct pypy_pypy_rlib_rstm_Transaction0 *t = t1;
    if (retry_counter > 0) {
        t->foobar = retry_counter;
        return NULL;
    }
    t->callback();
    t->foobar = 81;
    return NULL;
}
void run_in_transaction(void(*cb)(void), int expected)
{
    struct pypy_pypy_rlib_rstm_Transaction0 t;
    t.callback = cb;
    cb_run_transaction = rt2;
    stm_run_all_transactions(&t, 1);
    assert(t.foobar == expected);
}

void tldict(void)
{
    void *a1 = (void *)0x4020;
    void *a2 = (void *)10002;
    void *a3 = (void *)0x4028;
    void *a4 = (void *)10004;

    assert(stm_tldict_lookup(a1) == NULL);
    stm_tldict_add(a1, a2);
    assert(stm_tldict_lookup(a1) == a2);

    assert (stm_tldict_lookup(a3) == NULL);
    stm_tldict_add(a3, a4);
    assert(stm_tldict_lookup(a3) == a4);
    assert(stm_tldict_lookup(a1) == a2);
    stm_abort_and_retry();
}
void test_tldict(void)
{
    run_in_transaction(tldict, 1);
}


#define XTEST(name)  if (!strcmp(argv[1], #name)) { test_##name(); return 0; }

int main(int argc, char **argv)
{
    XTEST(set_get_del);
    XTEST(run_all_transactions);
    XTEST(tldict);
    printf("bad test name\n");
    return 1;
}
