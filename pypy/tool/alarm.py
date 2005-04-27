
import traceback 

def _main_with_alarm():
    import sys, os
    import time
    import thread


    def timeout_thread(timeout):
        stderr = sys.stderr
        interrupt_main = thread.interrupt_main
        time.sleep(timeout)
        stderr.write("="*26 + "timeout" + "="*26 + "\n")
        interrupt_main()


    timeout = float(sys.argv[1])
    thread.start_new_thread(timeout_thread, (timeout,))
    del sys.argv[:2]
    sys.path.insert(0, os.path.dirname(sys.argv[0]))
    return sys.argv[0]

execfile(_main_with_alarm())
