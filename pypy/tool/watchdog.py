import sys, os, signal
import threading

timeout = float(sys.argv[1])

def childkill():
    sys.stderr.write("="*26 + "timedout" + "="*26 + "\n")
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

pid = os.fork()
if pid == 0:
    os.execvp(sys.argv[2], sys.argv[2:])
else: # parent
    t = threading.Timer(timeout, childkill)
    t.start()
    while True:
        try:
            pid, status = os.waitpid(pid, 0)
        except KeyboardInterrupt:
            continue
        else:
            t.cancel()
            break
    if os.WIFEXITED(status):
        sys.exit(os.WEXITSTATUS(status))
    else:
        sys.exit(1)

    
    
