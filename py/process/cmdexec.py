"""

module defining basic hook for executing commands
in a - as much as possible - platform independent way. 

Current list:

    exec_cmd(cmd)       executes the given command and returns output
                        or ExecutionFailed exception (if exit status!=0)

"""

import os, sys

#-----------------------------------------------------------
# posix external command execution
#-----------------------------------------------------------
def posix_exec_cmd(cmd):
    """ return output of executing 'cmd'.

    raise ExecutionFailed exeception if the command failed.
    the exception will provide an 'err' attribute containing
    the error-output from the command.
    """
    import popen2

    #print "execing", cmd
    child = popen2.Popen3(cmd, 1)
    stdin, stdout, stderr = child.tochild, child.fromchild, child.childerr
    stdin.close()

    # XXX sometimes we get a blocked r.read() call (see below)
    #     although select told us there is something to read. 
    #     only the next three lines appear to prevent 
    #     the read call from blocking infinitely.
    import fcntl
    fcntl.fcntl(stdout, fcntl.F_SETFL, os.O_NONBLOCK)
    fcntl.fcntl(stderr, fcntl.F_SETFL, os.O_NONBLOCK)

    import select
    out, err = [], []
    while 1:
        r_list = filter(lambda x: x and not x.closed, [stdout, stderr])
        if not r_list:
            break
        r_list = select.select(r_list, [], [])[0]
        for r  in r_list:
            data = r.read()   # XXX see XXX above
            if not data:
                r.close()
                continue
            if r is stdout:
                out.append(data)
            else:
                err.append(data)
    pid, systemstatus = os.waitpid(child.pid, 0)
    if pid != child.pid:
        raise ExecutionFailed, "child process disappeared during: "+ cmd
    if systemstatus:
        if os.WIFSIGNALED(systemstatus):
            status = os.WTERMSIG(systemstatus) + 128
        else:
            status = os.WEXITSTATUS(systemstatus)
        raise ExecutionFailed(status, systemstatus, cmd, 
                              ''.join(out), ''.join(err))
    return "".join(out)

#-----------------------------------------------------------
# simple win32 external command execution
#-----------------------------------------------------------
def win32_exec_cmd(cmd):
    """ return output of executing 'cmd'.

    raise ExecutionFailed exeception if the command failed.
    the exception will provide an 'err' attribute containing
    the error-output from the command.

    Note that this method can currently deadlock because
    we don't have WaitForMultipleObjects in the std-python api.
    """
    stdin, stdout, stderr = os.popen3(cmd)
    out = stdout.read()
    err = stderr.read()
    stdout.close()
    stderr.close()
    status = stdin.close()
    if status:
        raise ExecutionFailed(status, status, cmd, out, err)
    return out


class ExecutionFailed(Exception):
    def __init__(self, status, systemstatus, cmd, out, err):
        Exception.__init__(self)
        self.status = status
        self.systemstatus = systemstatus
        self.cmd = cmd
        self.err = err
        self.out = out
            
    def __str__(self):
        return "ExecutionFailed: %d  %s\n%s" %(self.status, self.cmd, self.err)
#
# choose correct platform-version 
#
if sys.platform == 'win32':
    cmdexec = win32_exec_cmd
else:
    cmdexec = posix_exec_cmd

cmdexec.Error = ExecutionFailed
