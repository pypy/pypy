import os

def restartable_point():
    while True:
        while True:
            print '---> Checkpoint: run / quit / pdb ?'
            try:
                line = raw_input().strip().lower()
            except KeyboardInterrupt:
                print '(KeyboardInterrupt ignored)'
                continue
            if line == 'run':
                break
            if line == 'quit':
                raise SystemExit
            if line == 'pdb':
                import pdb; pdb.set_trace()

        pid = os.fork()
        if pid != 0:
            # in parent
            while True:
                try:
                    pid, status = os.waitpid(pid, 0)
                except KeyboardInterrupt:
                    continue
                else:
                    break
            print
            print '_'*78
            print 'Child %d exited' % pid,
            if os.WIFEXITED(status):
                print '(exit code %d)' % os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                print '(caught signal %d)' % os.WTERMSIG(status)
            else:
                print 'abnormally (status 0x%x)' % status
            continue

        # in child
        print '_'*78
        break


if __name__ == '__main__':
    print 'doing stuff...'
    print 'finished'
    restartable_point()
    print 'doing more stuff'
    print 'press Enter to quit...'
    raw_input()
