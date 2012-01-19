import thread


def allocate_lock():
    "NOT_RPYTHON"
    return thread.allocate_lock()

def acquire(lock, wait):
    "NOT_RPYTHON"
    lock.acquire(wait)

def release(lock):
    "NOT_RPYTHON"
    lock.release()

def start_new_thread(callback, args):
    "NOT_RPYTHON"
    thread.start_new_thread(callback, args)

