#include <stddef.h>

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

typedef struct {
    struct pypy_header0 header;
    char value1;
    short value2;
    int value4;
    long long value8;
    double value8f;
    float value4f;
    char last_16_bytes[16];
} S1;

typedef char bool_t;


#include "src_stm/et.h"
#include "src_stm/et.c"


long (*cb_getsize)(void *);
void (*cb_enum_callback)(void *, void *, void *);

long pypy_g__stm_getsize(void *a) {
    assert(cb_getsize != NULL);
    return cb_getsize(a);
}
void pypy_g__stm_enum_callback(void *a, void *b, void *c) {
    assert(cb_enum_callback != NULL);
    cb_enum_callback(a, b, c);
}


static long rt2(void *t1, long retry_counter)
{
    struct pypy_pypy_rlib_rstm_Transaction0 *t = t1;
    if (retry_counter > 0) {
        t->foobar = retry_counter;
        return 0;
    }
    t->callback();
    t->foobar = '.';
    return 0;
}
void run_in_transaction(void(*cb)(void), int expected)
{
    struct pypy_pypy_rlib_rstm_Transaction0 t;
    void *dummy;
    t.callback = cb;
    stm_perform_transaction(rt2, &t, &dummy);
    assert(t.foobar == expected);
}

/************************************************************/

void test_set_get_del(void)
{
    stm_set_tls((void *)42);
    assert(stm_get_tls() == (void *)42);
    stm_del_tls();
}

/************************************************************/

static long rt1(void *t1, long retry_counter)
{
    struct pypy_pypy_rlib_rstm_Transaction0 *t = t1;
    assert(retry_counter == 0);
    assert(t->foobar == 42);
    t->foobar = 143;
    return 0;
}
void test_run_all_transactions(void)
{
    struct pypy_pypy_rlib_rstm_Transaction0 t;
    void *dummy;
    t.foobar = 42;
    stm_perform_transaction(rt1, &t, &dummy);
    assert(t.foobar == 143);
}

/************************************************************/

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
void test_tldict(void) { run_in_transaction(tldict, 1); }

/************************************************************/

void tldict_large(void)
{
    void *content[4096] = { 0 };
    int i;
    for (i=0; i<120000; i++) {
        long key_index = rand() & 4095;
        void *a1 = (void *)(10000 + key_index * 8);
        void *a2 = stm_tldict_lookup(a1);

        if (content[key_index] != NULL) {
            assert(a2 == content[key_index]);
        }
        else {
            assert(a2 == NULL);
            while (a2 == NULL)
                a2 = (void *)rand();
            stm_tldict_add(a1, a2);
            content[key_index] = a2;
        }
    }
    stm_abort_and_retry();
}
void test_tldict_large(void) { run_in_transaction(tldict_large, 1); }

/************************************************************/

void enum_tldict_empty(void)
{
    stm_tldict_enum();
}
void test_enum_tldict_empty(void) {
    run_in_transaction(enum_tldict_empty, '.'); }

/************************************************************/

int check_enum_1_found;
void check_enum_1(void *tls, void *a, void *b)
{
    int n;
    assert(tls == (void *)742);
    if (a == (void *)0x4020 && b == (void *)10002)
        n = 1;
    else if (a == (void *)0x4028 && b == (void *)10004)
        n = 2;
    else
        assert(!"unexpected a or b");
    assert((check_enum_1_found & n) == 0);
    check_enum_1_found |= n;
}
void enum_tldict_nonempty(void)
{
    void *a1 = (void *)0x4020;
    void *a2 = (void *)10002;
    void *a3 = (void *)0x4028;
    void *a4 = (void *)10004;

    stm_set_tls((void *)742);
    stm_tldict_add(a1, a2);
    stm_tldict_add(a3, a4);
    cb_enum_callback = check_enum_1;
    check_enum_1_found = 0;
    stm_tldict_enum();
    assert(check_enum_1_found == (1|2));
    stm_abort_and_retry();
}
void test_enum_tldict_nonempty(void) {
    run_in_transaction(enum_tldict_nonempty, 1); }

/************************************************************/

void test_read_main_thread(void)
{
    S1 s1;
    int i;
    stm_begin_inevitable_transaction();
    for (i=0; i<2; i++) {
        s1.header.h_tid = GCFLAG_GLOBAL | (i ? GCFLAG_WAS_COPIED : 0);
        s1.header.h_version = NULL;
        s1.value1 = 49;
        s1.value2 = 3981;
        s1.value4 = 4204229;
        s1.value8 = 3419103092099219LL;
        s1.value8f = 289.25;
        s1.value4f = -5.5;

        assert(stm_read_int1( &s1, offsetof(S1, value1 )) == 49);
        assert(stm_read_int2( &s1, offsetof(S1, value2 )) == 3981);
        assert(stm_read_int4( &s1, offsetof(S1, value4 )) == 4204229);
        assert(stm_read_int8( &s1, offsetof(S1, value8))== 3419103092099219LL);
        assert(stm_read_int8f(&s1, offsetof(S1, value8f)) == 289.25);
        assert(stm_read_int4f(&s1, offsetof(S1, value4f)) == -5.5);
    }
}

/************************************************************/

void read_transaction(void)
{
    S1 s1, s2;
    int i;
    for (i=0; i<2; i++) {
        s1.header.h_tid = GCFLAG_GLOBAL | (i ? GCFLAG_WAS_COPIED : 0);
        s1.header.h_version = NULL;
        s1.value1 = 49;
        s1.value2 = 3981;
        s1.value4 = 4204229;
        s1.value8 = 3419103092099219LL;
        s1.value8f = 289.25;
        s1.value4f = -5.5;

        assert(stm_read_int1( &s1, offsetof(S1, value1 )) == 49);
        assert(stm_read_int2( &s1, offsetof(S1, value2 )) == 3981);
        assert(stm_read_int4( &s1, offsetof(S1, value4 )) == 4204229);
        assert(stm_read_int8( &s1, offsetof(S1, value8))== 3419103092099219LL);
        assert(stm_read_int8f(&s1, offsetof(S1, value8f)) == 289.25);
        assert(stm_read_int4f(&s1, offsetof(S1, value4f)) == -5.5);
    }

    s1.header.h_tid = GCFLAG_GLOBAL | GCFLAG_WAS_COPIED;
    s1.header.h_version = NULL;
    s2.header.h_tid = GCFLAG_WAS_COPIED;
    s2.header.h_version = &s1;
    s2.value1 = -49;
    s2.value2 = -3981;
    s2.value4 = -4204229;
    s2.value8 = -3419103092099219LL;
    s2.value8f = -289.25;
    s2.value4f = 5.5;
    stm_tldict_add(&s1, &s2);

    assert(stm_read_int1( &s1, offsetof(S1, value1 )) == -49);
    assert(stm_read_int2( &s1, offsetof(S1, value2 )) == -3981);
    assert(stm_read_int4( &s1, offsetof(S1, value4 )) == -4204229);
    assert(stm_read_int8( &s1, offsetof(S1, value8))  == -3419103092099219LL);
    assert(stm_read_int8f(&s1, offsetof(S1, value8f)) == -289.25);
    assert(stm_read_int4f(&s1, offsetof(S1, value4f)) == 5.5);
    stm_abort_and_retry();
}
void test_read_transaction(void) { run_in_transaction(read_transaction, 1); }

/************************************************************/

int sg_seen = 0;
S1 sg_global;
void size_getter(void)
{
    S1 *s2 = malloc(sizeof(S1));
    int i;
    sg_global.header.h_tid = GCFLAG_GLOBAL | GCFLAG_WAS_COPIED;
    sg_global.header.h_version = NULL;
    s2->header.h_tid = GCFLAG_WAS_COPIED;
    s2->header.h_version = &sg_global;
    for (i=0; i<16; i++)
        s2->last_16_bytes[i] = 'A' + i;
    stm_tldict_add(&sg_global, s2);
}
long size_getter_cb(void *x)
{
    return offsetof(S1, last_16_bytes) + 15;
}
void test_size_getter(void)
{
    int i;
    cb_getsize = size_getter_cb;
    sg_global.last_16_bytes[15] = '!';
    run_in_transaction(size_getter, '.');
    for (i=0; i<15; i++)
        assert(sg_global.last_16_bytes[i] == 'A' + i);
    assert(sg_global.last_16_bytes[15] == '!');   /* not overwritten */
}

/************************************************************/

void copy_transactional_to_raw(void)
{
    S1 s1, s2;
    int i;
    s1.header.h_tid = GCFLAG_GLOBAL | 99;
    s1.header.h_version = NULL;
    for (i=0; i<16; i++)
        s1.last_16_bytes[i] = 'A' + i;
    s2.header.h_tid = 101;
    s2.last_16_bytes[15] = '!';
    stm_copy_transactional_to_raw(&s1, &s2, offsetof(S1, last_16_bytes) + 15);
    for (i=0; i<15; i++)
        assert(s2.last_16_bytes[i] == 'A' + i);
    assert(s2.last_16_bytes[15] == '!');   /* not overwritten */
    assert(s2.header.h_tid = 101);         /* not overwritten */
}
void test_copy_transactional_to_raw(void) {
    run_in_transaction(copy_transactional_to_raw, '.');
}

/************************************************************/

void try_inevitable(void)
{
    assert(stm_in_transaction() == 1);
    assert(!stm_is_inevitable());
    /* not really testing anything more than the presence of the function */
    stm_try_inevitable(STM_EXPLAIN1("some explanation"));
    assert(stm_is_inevitable());
}
void test_try_inevitable(void)
{
    assert(stm_in_transaction() == 0);
    run_in_transaction(try_inevitable, '.');
}

/************************************************************/


#define XTEST(name)  if (!strcmp(argv[1], #name)) { test_##name(); return 0; }

int main(int argc, char **argv)
{
    long res = stm_descriptor_init();
    assert(res == 1);
    XTEST(set_get_del);
    XTEST(run_all_transactions);
    XTEST(tldict);
    XTEST(tldict_large);
    XTEST(enum_tldict_empty);
    XTEST(enum_tldict_nonempty);
    XTEST(read_main_thread);
    XTEST(read_transaction);
    XTEST(size_getter);
    XTEST(copy_transactional_to_raw);
    XTEST(try_inevitable);
    printf("bad test name\n");
    return 1;
}
