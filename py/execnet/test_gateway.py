import os, sys
import py 
from py.__impl__.execnet.source import Source
from py.__impl__.execnet import gateway 
mypath = py.magic.autopath() 

from StringIO import StringIO

class TestMessage:
    def test_wire_protocol(self):
        for cls in gateway.Message._types.values():
            one = StringIO()
            cls(42, '23').writeto(one) 
            two = StringIO(one.getvalue())
            msg = gateway.Message.readfrom(two)
            assert isinstance(msg, cls) 
            assert msg.channelid == 42 
            assert msg.data == '23'
            assert isinstance(repr(msg), str)
            # == "<Message.%s channelid=42 '23'>" %(msg.__class__.__name__, )

class TestChannel:
    def setup_method(self, method):
        self.fac = gateway.ChannelFactory(None)

    def test_factory_create(self):
        chan1 = self.fac.new()
        assert chan1.id == 1
        chan2 = self.fac.new()
        assert chan2.id == 3

    def test_factory_getitem(self):
        chan1 = self.fac.new()
        assert self.fac[chan1.id] == chan1 
        chan2 = self.fac.new()
        assert self.fac[chan2.id] == chan2
        
    def test_factory_delitem(self):
        chan1 = self.fac.new()
        assert self.fac[chan1.id] == chan1 
        del self.fac[chan1.id]
        py.test.raises(KeyError, self.fac.__getitem__, chan1.id)

    def test_factory_setitem(self):
        channel = gateway.Channel(None, 12)
        self.fac[channel.id] = channel
        assert self.fac[channel.id] == channel 

    def test_channel_timeouterror(self):
        channel = self.fac.new() 
        py.test.raises(IOError, channel.waitclose, timeout=0.01)

    def test_channel_close(self):
        channel = self.fac.new()
        channel._close() 
        channel.waitclose(0.1)

    def test_channel_close_error(self):
        channel = self.fac.new()
        channel._close("error") 
        py.test.raises(gateway.RemoteError, channel.waitclose, 0.01) 

class PopenGatewayTestSetup: 
    def setup_class(cls):
        cls.gw = py.execnet.PopenGateway() 

    def teardown_class(cls):
        cls.gw.exit()  

class BasicRemoteExecution: 
    def test_correct_setup(self):
        assert self.gw.workerthreads and self.gw.iothreads 

    def test_remote_exec_waitclose(self): 
        channel = self.gw.remote_exec('pass') 
        channel.waitclose(timeout=3.0) 

    def test_remote_exec_channel_anonymous(self):
        channel = self.gw.remote_exec('''
                    obj = channel.receive()
                    channel.send(obj)
                  ''')
        channel.send(42)
        result = channel.receive()
        assert result == 42

    def test_channel_close_and_then_receive_error(self):
        channel = self.gw.remote_exec('raise ValueError')
        py.test.raises(gateway.RemoteError, channel.receive) 

    def test_channel_close_and_then_receive_error_multiple(self):
        channel = self.gw.remote_exec('channel.send(42) ; raise ValueError')
        import time
        time.sleep(0.1)
        x = channel.receive()
        assert x == 42 
        py.test.raises(gateway.RemoteError, channel.receive) 

class TestBasicPopenGateway(PopenGatewayTestSetup, BasicRemoteExecution): 
    def test_many_popen(self):
        num = 4
        l = []
        for i in range(num):
            l.append(py.execnet.PopenGateway())
        channels = []
        for gw in l: 
            channel = gw.remote_exec("""channel.send(42)""")
            channels.append(channel)
        try:
            while channels: 
                channel = channels.pop()
                try:
                    ret = channel.receive()
                    assert ret == 42
                finally:
                    channel.gateway.exit()
        finally:
            for x in channels: 
                x.gateway.exit()

class SocketGatewaySetup:
    def setup_class(cls):
        portrange = (7770, 7800)
        cls.proxygw = py.execnet.PopenGateway() 
        socketserverbootstrap = Source( 
            mypath.dirpath('bin', 'startserver.py').read(), 
            """
            import socket 
            portrange = channel.receive() 
            for i in portrange: 
                try:
                    sock = bind_and_listen(("localhost", i))
                except socket.error: 
                    print "got error"
                    import traceback
                    traceback.print_exc()
                    continue
                else:
                    channel.send(i) 
                    startserver(sock)
                    break
            else:
                channel.send(None) 
    """)
        # open a gateway to a fresh child process 
        cls.proxygw = py.execnet.PopenGateway()

        # execute asynchronously the above socketserverbootstrap on the other
        channel = cls.proxygw.remote_exec(socketserverbootstrap) 

        # send parameters for the for-loop
        channel.send((7770, 7800)) 
        #
        # the other side should start the for loop now, we
        # wait for the result
        #
        cls.listenport = channel.receive() 
        if cls.listenport is None: 
            raise IOError, "could not setup remote SocketServer"
        cls.gw = py.execnet.SocketGateway('localhost', cls.listenport) 
        print "initialized socket gateway on port", cls.listenport 

    def teardown_class(cls):
        print "trying to tear down remote socket gateway" 
        cls.gw.exit() 
        if cls.gw.port: 
            print "trying to tear down remote socket loop" 
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', cls.listenport))
            sock.sendall('"raise KeyboardInterrupt"') 
            sock.shutdown(2) 
        print "trying to tear proxy gateway" 
        cls.proxygw.exit() 

class TestSocketGateway(SocketGatewaySetup, BasicRemoteExecution): 
    pass
