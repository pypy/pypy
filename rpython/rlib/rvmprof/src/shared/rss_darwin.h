/* On OS X we can get RSS using the Mach API. */
#include <mach/mach.h>
#include <mach/message.h>
#include <mach/kern_return.h>
#include <mach/task_info.h>

static mach_port_t mach_task;

static int setup_rss(void)
{
    mach_task = mach_task_self();
    return 0;
}

static int teardown_rss(void)
{
    return 0;
}

static long get_current_proc_rss(void)
{
    mach_msg_type_number_t out_count = MACH_TASK_BASIC_INFO_COUNT;
    mach_task_basic_info_data_t taskinfo = { .resident_size = 0 };

    kern_return_t error = task_info(mach_task, MACH_TASK_BASIC_INFO, (task_info_t)&taskinfo, &out_count);
    if (error == KERN_SUCCESS) {
        return taskinfo.resident_size / 1024;
    } else {
        return -1;
    }
}
