#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <sys/time.h>
#include <errno.h>
#ifdef PTEST_USE_THREAD
# include <pthread.h>
# include <semaphore.h>
sem_t *done;
#endif


extern int add1(int, int);


static double time_delta(struct timeval *stop, struct timeval *start)
{
    return (stop->tv_sec - start->tv_sec) +
        1e-6 * (stop->tv_usec - start->tv_usec);
}

static double measure(void)
{
    long long i, iterations;
    int result;
    struct timeval start, stop;
    double elapsed;

    add1(0, 0);   /* prepare off-line */

    i = 0;
    iterations = 1000;
    result = gettimeofday(&start, NULL);
    assert(result == 0);

    while (1) {
        for (; i < iterations; i++) {
            add1(((int)i) & 0xaaaaaa, ((int)i) & 0x555555);
        }
        result = gettimeofday(&stop, NULL);
        assert(result == 0);

        elapsed = time_delta(&stop, &start);
        assert(elapsed >= 0.0);
        if (elapsed > 2.5)
            break;
        iterations = iterations * 3 / 2;
    }

    return elapsed / (double)iterations;
}

static void *start_routine(void *arg)
{
    double t = measure();
    printf("time per call: %.3g\n", t);

#ifdef PTEST_USE_THREAD
    int status = sem_post(done);
    assert(status == 0);
#endif

    return arg;
}


int main(void)
{
#ifndef PTEST_USE_THREAD
    start_routine(0);
#else
    pthread_t th;
    done = sem_open("perf-test", O_CREAT, 0777, 0);
    int i, status;

    add1(0, 0);   /* this is the main thread */

    for (i = 0; i < PTEST_USE_THREAD; i++) {
        status = pthread_create(&th, NULL, start_routine, NULL);
        assert(status == 0);
    }
    for (i = 0; i < PTEST_USE_THREAD; i++) {
        status = sem_wait(done);
        if (status)
            fprintf(stderr, "%s\n", strerror(errno));
        assert(status == 0);
    }
#endif
    return 0;
}
