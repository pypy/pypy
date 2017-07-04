#ifdef VMPROF_UNIX

#include <unistd.h>
/* value: LSB bit is 1 if signals must be ignored; all other bits
   are a counter for how many threads are currently in a signal handler */
static long volatile signal_handler_value = 1;

void vmprof_ignore_signals(int ignored)
{
    if (!ignored) {
        __sync_fetch_and_and(&signal_handler_value, ~1L);
    } else {
        /* set the last bit, and wait until concurrently-running signal
           handlers finish */
        while (__sync_or_and_fetch(&signal_handler_value, 1L) != 1L) {
            usleep(1);
        }
    }
}

long vmprof_enter_signal(void)
{
    return __sync_fetch_and_add(&signal_handler_value, 2L);
}

long vmprof_exit_signal(void)
{
    return __sync_sub_and_fetch(&signal_handler_value, 2L);
}
#endif
