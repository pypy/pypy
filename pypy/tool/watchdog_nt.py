import sys, os
import threading
import ctypes

PROCESS_TERMINATE = 0x1

timeout = float(sys.argv[1])
timedout = False

def childkill(pid):
    global timedout
    timedout = True
    sys.stderr.write("==== test running for %d seconds ====\n" % timeout)
    sys.stderr.write("="*26 + "timedout" + "="*26 + "\n")
    ctypes.windll.kernel32.TerminateProcess(pid, 1)

pid = os.spawnv(os.P_NOWAIT, sys.argv[2], sys.argv[2:])

t = threading.Timer(timeout, childkill, (pid,))
t.start()
while True:
    try:
        pid, status = os.waitpid(pid, 0)
    except KeyboardInterrupt:
        continue
    else:
        t.cancel()
        break

#print 'status ', status >> 8
sys.exit(status >> 8)
    
