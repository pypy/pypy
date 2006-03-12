#include <unistd.h>
#include <stdio.h>

#define N 100000000

#if defined(__GNUC__) && defined(_POSIX_THREADS)
#include <pthread.h>

void * th_f(void *x) {
        volatile int * n = (volatile int *)x;
        static __thread int i = 0;
        int  delta;
        delta = *n;
        for (; i < N; i++) {
                *n += delta;
        }
        return NULL;
}

int nbs[] = {2, 3};

int main() {
        pthread_t t0, t1;
        pthread_create(&t0, NULL, th_f, &nbs[0]);
        pthread_create(&t1, NULL, th_f, &nbs[1]);
        pthread_join(t0, NULL);
        pthread_join(t1, NULL);
        printf("1= %d\n", nbs[0]);
        printf("2= %d\n", nbs[1]);
        return !(nbs[0] == (N+1)*2 && nbs[1] == (N+1)*3);
}

#else
#error "Meaningful only with GCC (+ POSIX Threads)"
#endif
