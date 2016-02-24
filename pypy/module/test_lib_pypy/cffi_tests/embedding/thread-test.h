/************************************************************/
#ifndef _MSC_VER
/************************************************************/


#include <pthread.h>
#include <semaphore.h>


/************************************************************/
#else
/************************************************************/


/* Very quick and dirty, just what I need for these tests.
   Don't use directly in any real code! 
*/

#include <Windows.h>
#include <assert.h>

typedef HANDLE sem_t;
typedef HANDLE pthread_t;

int sem_init(sem_t *sem, int pshared, unsigned int value)
{
    assert(pshared == 0);
    assert(value == 0);
    *sem = CreateSemaphore(NULL, 0, 999, NULL);
    return *sem ? 0 : -1;
}

int sem_post(sem_t *sem)
{
    return ReleaseSemaphore(*sem, 1, NULL) ? 0 : -1;
}

int sem_wait(sem_t *sem)
{
    WaitForSingleObject(*sem, INFINITE);
    return 0;
}

DWORD WINAPI myThreadProc(LPVOID lpParameter)
{
    void *(* start_routine)(void *) = (void *(*)(void *))lpParameter;
    start_routine(NULL);
    return 0;
}

int pthread_create(pthread_t *thread, void *attr,
                   void *start_routine(void *), void *arg)
{
    assert(arg == NULL);
    *thread = CreateThread(NULL, 0, myThreadProc, start_routine, 0, NULL);
    return *thread ? 0 : -1;
}


/************************************************************/
#endif
/************************************************************/
