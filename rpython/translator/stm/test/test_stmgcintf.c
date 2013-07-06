#define _GNU_SOURCE
#define _XOPEN_SOURCE 500

#include <stddef.h>

#define PYPY_LONG_BIT   (sizeof(long) * 8)

typedef long Signed;
typedef unsigned long Unsigned;

struct pypy_header0 {
    long h_tid;
    Unsigned h_revision;
	Unsigned h_original;
};

struct pypy_pypy_rlib_rstm_Transaction0 {
    struct pypy_header0 header;
    struct pypy_pypy_rlib_rstm_Transaction0 *t_inst__next_transaction;
    void *stack_root_top;
    int foobar;
    void (*callback)(void);
    void *stack_roots[3];
};

typedef struct {
    struct pypy_header0 header;
    char value1;
} S1;

typedef char bool_t;
typedef char RPyString;

#define _RPyString_AsString(x) x
#define RPyString_Size(x) strlen(x)

#include "src_stm/stmgc.h"
#include "src_stm/stmimpl.h"
#include "src_stm/et.h"
#include "src_stm/et.c"


gcptr (*cb_duplicate)(gcptr);
void (*cb_enum_callback)(void *, gcptr);

void *pypy_g__stm_duplicate(void *a) {
    assert(cb_duplicate != NULL);
    return cb_duplicate((gcptr)a);
}
void pypy_g__stm_enum_callback(void *a, void *b) {
    assert(cb_enum_callback != NULL);
    cb_enum_callback(a, (gcptr)b);
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
    t.stack_root_top = t.stack_roots;
    t.callback = cb;
    stm_perform_transaction(rt2, &t, &t.stack_root_top);
    assert(t.foobar == expected);
}

/************************************************************/

void test_bool_cas(void)
{
    volatile Unsigned bv = 10;

    assert(bool_cas(&bv, 10, 15));
    assert(bv == 15);
    assert(!bool_cas(&bv, 10, 15));
    assert(bv == 15);
    assert(!bool_cas(&bv, 10, 25));
    assert(bv == 15);
    assert(bool_cas(&bv, 15, 14));
    assert(bv == 14);
}

void test_fetch_and_add(void)
{
    volatile Unsigned bv = 14;

    assert(fetch_and_add(&bv, 2) == 14);
    assert(bv == 16);
    assert(fetch_and_add(&bv, 7) == 16);
    assert(fetch_and_add(&bv, (Unsigned)-1) == 23);
    assert(bv == 22);
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
    assert(t->stack_root_top == t->stack_roots + 1);
    assert(t->stack_roots[0] == (void*)-8);    /* END_MARKER */
    assert(t->stack_roots[1] == (void*)43);
    assert(t->stack_roots[2] == (void*)44);
    t->foobar = 143;
    return 0;
}
void test_run_all_transactions(void)
{
    struct pypy_pypy_rlib_rstm_Transaction0 t;
    t.stack_root_top = t.stack_roots;
    t.stack_roots[0] = (void*)42;
    t.stack_roots[1] = (void*)43;
    t.stack_roots[2] = (void*)44;
    t.foobar = 42;
    stm_perform_transaction(rt1, &t, &t.stack_root_top);
    assert(t.foobar == 143);
    assert(t.stack_root_top == t.stack_roots);
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

struct pypy_header0 etldn1 = {GCFLAG_PREBUILT, REV_INITIAL};
struct pypy_header0 etldn2 = {GCFLAG_LOCAL_COPY, (revision_t)&etldn1};
struct pypy_header0 etldn3 = {GCFLAG_PREBUILT, REV_INITIAL};
struct pypy_header0 etldn4 = {GCFLAG_LOCAL_COPY, (revision_t)&etldn3};

int check_enum_1_found;
void check_enum_1(void *tls, gcptr b)
{
    int n;
    gcptr a = (gcptr)b->h_revision;
    assert(tls == (void *)742);
    if (a == &etldn1 && b == &etldn2)
        n = 1;
    else if (a == &etldn3 && b == &etldn4)
        n = 2;
    else
        assert(!"unexpected a or b");
    assert((check_enum_1_found & n) == 0);
    check_enum_1_found |= n;
}
void enum_tldict_nonempty(void)
{
    stm_set_tls((void *)742);
    stm_tldict_add(&etldn1, &etldn2);
    stm_tldict_add(&etldn3, &etldn4);
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
    S1 *p2;
    int i;
    BeginInevitableTransaction();
    for (i=0; i<2; i++) {
        s1.header.h_tid = GCFLAG_PREBUILT | (i ? GCFLAG_POSSIBLY_OUTDATED : 0);
        s1.header.h_revision = REV_INITIAL;

        p2 = STM_BARRIER_P2R(&s1);
        assert(p2 == &s1);

        p2 = STM_BARRIER_G2R(&s1);
        assert(p2 == &s1);
    }
}

/************************************************************/

void read_transaction(void)
{
    S1 s1, s2;
    S1 *p2;
    int i;
    for (i=0; i<2; i++) {
        s1.header.h_tid = GCFLAG_PREBUILT | (i ? GCFLAG_POSSIBLY_OUTDATED : 0);
        s1.header.h_revision = REV_INITIAL;

        p2 = STM_BARRIER_P2R(&s1);
        assert(p2 == &s1);

        p2 = STM_BARRIER_G2R(&s1);
        assert(p2 == &s1);
    }

    s1.header.h_tid = GCFLAG_PREBUILT | GCFLAG_POSSIBLY_OUTDATED;
    s1.header.h_revision = REV_INITIAL;
    s2.header.h_tid = GCFLAG_LOCAL_COPY;
    s2.header.h_revision = (revision_t)&s1;
    stm_tldict_add(&s1.header, &s2.header);

    p2 = STM_BARRIER_P2R(&s1);
    assert(p2 == &s2);

    p2 = STM_BARRIER_G2R(&s1);
    assert(p2 == &s2);

    p2 = STM_BARRIER_O2R(&s1);
    assert(p2 == &s2);

    p2 = STM_BARRIER_P2R(&s2);
    assert(p2 == &s2);

    p2 = STM_BARRIER_O2R(&s2);
    assert(p2 == &s2);

    stm_abort_and_retry();
}
void test_read_transaction(void) { run_in_transaction(read_transaction, 1); }

/************************************************************/

int sg_seen = 0;
S1 sg_global, sg_local;
void duplicator(void)
{
    S1 *s2;
    int i;
    sg_global.header.h_tid = GCFLAG_PREBUILT | GCFLAG_POSSIBLY_OUTDATED;
    sg_global.header.h_revision = REV_INITIAL;
    sg_global.value1 = 123;

    s2 = STM_BARRIER_P2W(&sg_global);
    assert(s2 == &sg_local);
    assert(s2->header.h_tid == GCFLAG_LOCAL_COPY | GCFLAG_VISITED);
    assert(s2->header.h_revision == (revision_t)&sg_global);
    assert(s2->value1 == 123);
}
gcptr duplicator_cb(gcptr x)
{
    assert(x == &sg_global.header);
    sg_local = sg_global;
    sg_local.header.h_tid &= ~(GCFLAG_GLOBAL | GCFLAG_POSSIBLY_OUTDATED);
    sg_local.header.h_tid |= GCFLAG_LOCAL_COPY | GCFLAG_VISITED;
    return &sg_local.header;
}
void test_duplicator(void)
{
    cb_duplicate = duplicator_cb;
    run_in_transaction(duplicator, '.');
}

/************************************************************/

void try_inevitable(void)
{
    assert(stm_in_transaction() == 1);
    assert(!stm_is_inevitable());
    /* not really testing anything more than the presence of the function */
    BecomeInevitable("some explanation");
    assert(stm_is_inevitable());
}
void test_try_inevitable(void)
{
    assert(stm_in_transaction() == 0);
    run_in_transaction(try_inevitable, '.');
}

/************************************************************/

void should_break_transaction_1(void)
{
    assert(stm_should_break_transaction() == 0);
    stm_set_transaction_length(10);   /* implies "becomes inevitable" */
    assert(stm_should_break_transaction() == 1);
}

void should_break_transaction_2(void)
{
    S1 s1[15];
    int i;
    for (i=0; i<15; i++) {
        s1[i].header.h_tid = GCFLAG_PREBUILT;
        s1[i].header.h_revision = REV_INITIAL;
        s1[i].value1 = 48+i;
    }
    for (i=0; i<15; i++) {
        S1 *p = STM_BARRIER_P2R(&s1[i]);
        assert(p->value1 == 48+i);
        assert(stm_should_break_transaction() == ((i+1) >= 10));
    }
}

void test_should_break_transaction(void)
{
    assert(stm_in_transaction() == 0);
    run_in_transaction(should_break_transaction_1, '.');
    run_in_transaction(should_break_transaction_2, '.');
}

/************************************************************/

void single_thread_1(void)
{
    stm_start_single_thread();
    stm_stop_single_thread();
    stm_start_single_thread();
    stm_stop_single_thread();
    /* check that the assert() included in these functions don't trigger */
}

void test_single_thread(void)
{
    run_in_transaction(single_thread_1, '.');
}

/************************************************************/


#define XTEST(name)  if (!strcmp(argv[1], #name)) { test_##name(); return 0; }

int main(int argc, char **argv)
{
    XTEST(bool_cas);
    XTEST(fetch_and_add);

    DescriptorInit();
    XTEST(set_get_del);
    XTEST(run_all_transactions);
    XTEST(tldict);
    XTEST(tldict_large);
    XTEST(enum_tldict_empty);
    XTEST(enum_tldict_nonempty);
    XTEST(read_main_thread);
    XTEST(read_transaction);
    XTEST(duplicator);
    XTEST(try_inevitable);
    XTEST(should_break_transaction);
    XTEST(single_thread);
    printf("bad test name\n");
    return 1;
}
