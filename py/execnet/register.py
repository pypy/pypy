
from py.magic import autopath ; autopath = autopath()
import os, inspect, socket
import sys

import py
from py.__impl__.execnet import inputoutput, gateway

class InstallableGateway(gateway.Gateway):
    """ initialize gateways on both sides of a inputoutput object. """
    def __init__(self, io): 
        self.remote_bootstrap_gateway(io) 
        gateway.Gateway.__init__(self, io=io, startcount=1)

    def remote_bootstrap_gateway(self, io): 
        """ return Gateway with a asynchronously remotely 
            initialized counterpart Gateway (which may or may not succeed). 
            Note that the other sides gateways starts enumerating 
            its channels with even numbers while the sender
            gateway starts with odd numbers.  This allows to 
            uniquely identify channels across both sides. 
        """
        bootstrap = [ 
            inspect.getsource(inputoutput), 
            inspect.getsource(gateway), 
            io.server_stmt, 
            "Gateway(io=io, startcount=2).join()", 
        ]
        source = "\n".join(bootstrap)
        self.trace("sending gateway bootstrap code")
        io.write('%r\n' % source)

class PopenGateway(InstallableGateway):
    def __init__(self, python=sys.executable): 
        cmd = '%s -u -c "exec input()"' % python
        infile, outfile = os.popen2(cmd)
        io = inputoutput.Popen2IO(infile, outfile) 
        InstallableGateway.__init__(self, io=io) 
        self._pidchannel = self.remote_exec("import os ; channel.send(os.getpid())")

    def exit(self):
        super(PopenGateway, self).exit()
        try:
            self._pidchannel.waitclose(timeout=0.5) 
            pid = self._pidchannel.receive()
        except IOError: 
            self.trace("could not receive child PID")
        else:
            self.trace("waiting for pid %s" % pid) 
            try:
                os.waitpid(pid, 0) 
            except OSError: 
                self.trace("child process %s already dead?" %pid) 

class SocketGateway(InstallableGateway):
    def __init__(self, host, port): 
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host = str(host) 
        self.port = port = int(port) 
        sock.connect((host, port))
        io = inputoutput.SocketIO(sock) 
        InstallableGateway.__init__(self, io=io) 
        
class ExecGateway(PopenGateway):
    def remote_exec_sync_stdcapture(self, lines, callback):
        # hack: turn the content of the cell into
        #
        # if 1:
        #    line1
        #    line2
        #    ...
        #
        lines = ['   ' + line for line in lines]
        lines.insert(0, 'if 1:')
        lines.append('')
        sourcecode = '\n'.join(lines)
        try:
            callbacks = self.callbacks
        except AttributeError:
            callbacks = self.callbacks = {}
        answerid = id(callback)
        self.callbacks[answerid] = callback
        
        self.exec_remote('''
            import sys, StringIO
            try:
                execns
            except:
                execns = {}
            oldout, olderr = sys.stdout, sys.stderr
            try:
                buffer = StringIO.StringIO()
                sys.stdout = sys.stderr = buffer
                try:
                    exec compile(%(sourcecode)r, 'single') in execns
                except:
                    import traceback
                    traceback.print_exc()
            finally:
                sys.stdout=oldout
                sys.stderr=olderr
            # fiddle us (the caller) into executing the callback on remote answers
            gateway.exec_remote(
                "gateway.invoke_callback(%(answerid)r, %%r)" %% buffer.getvalue())
        ''' % locals())

    def invoke_callback(self, answerid, value):
        callback = self.callbacks[answerid]
        del self.callbacks[answerid]
        callback(value)
