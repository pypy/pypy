import sys, os, threading, struct, Queue, traceback
import atexit

# XXX the following line should not be here
from py.__impl__.execnet.source import Source

debug = 0
sysex = (KeyboardInterrupt, SystemExit) 

class RemoteError(Exception):
    """ Contains an Exceptions from the other side. """
    def __init__(self, formatted): 
        Exception.__init__(self) 
        self.formatted = formatted 

    def __str__(self):
        return self.formatted 

    def __repr__(self):
        return "%s: %s" %(self.__class__.__name__, self.formatted) 

class Gateway(object):
    num_worker_threads = 2
    RemoteError = RemoteError

    def __init__(self, io, startcount=2): 
        self.io = io
        self._execqueue = Queue.Queue()
        self._outgoing = Queue.Queue()
        self.channelfactory = ChannelFactory(self, startcount) 
        self.iothreads = [
            threading.Thread(target=self.thread_receiver, name='receiver'),
            threading.Thread(target=self.thread_sender, name='sender'),
        ]
        self.workerthreads = w = [] 
        for x in range(self.num_worker_threads):
            w.append(threading.Thread(target=self.thread_executor, 
                                      name='executor %d' % x))
        for x in self.iothreads + w: 
            x.start()
        if not _gateways:
            atexit.register(cleanup_atexit) 
        _gateways.append(self) 

    def _stopexec(self):
        if self.workerthreads: 
            for x in self.workerthreads: 
                self._execqueue.put(None) 
            for x in self.workerthreads:
                if x.isAlive():
                    self.trace("joining %r" % x)
                    x.join()
            self.workerthreads[:] = []

    def exit(self): 
        if self.workerthreads:
            self._stopexec()
            self._outgoing.put(Message.EXIT_GATEWAY()) 
        else:
            self.trace("exit() called, but gateway has not threads anymore!") 

    def join(self):
        current = threading.currentThread()
        for x in self.iothreads: 
            if x != current and x.isAlive():
                print "joining", x
                x.join()

    def trace(self, *args):
        if debug:
            try:
                l = "\n".join(args).split(os.linesep)
                id = getid(self)
                for x in l:
                    print id, x 
            except sysex: 
                raise
            except:
                import traceback
                traceback.print_exc()
    def traceex(self, excinfo):
        l = traceback.format_exception(*excinfo) 
        errortext = "".join(l)
        self.trace(errortext)

    def thread_receiver(self):
        """ thread to read and handle Messages half-sync-half-async. """ 
        try:
            while 1: 
                try:
                    msg = Message.readfrom(self.io) 
                    self.trace("received <- %r" % msg) 
                    msg.received(self) 
                except sysex: 
                    raise 
                except:
                    self.traceex(sys.exc_info()) 
                    break
        finally:
            self.trace('leaving %r' % threading.currentThread())

    def thread_sender(self):
        """ thread to send Messages over the wire. """ 
        try:
            while 1: 
                msg = self._outgoing.get()
                try:
                    msg.writeto(self.io) 
                except: 
                    excinfo = sys.exc_info()
                    self.traceex(excinfo) 
                    msg.post_sent(self, excinfo) 
                    raise
                else:
                    self.trace('sent -> %r' % msg) 
                    msg.post_sent(self)
        finally: 
            self.trace('leaving %r' % threading.currentThread())

    def thread_executor(self):
        """ worker thread to execute source objects from the execution queue. """ 
        try:
            while 1: 
                task = self._execqueue.get()
                if task is None: 
                    break
                channel, source = task 
                try:
                    loc = { 'channel' : channel } 
                    self.trace("execution starts:", repr(source)[:50]) 
                    try: 
                        co = compile(source+'\n', '', 'exec')
                        exec co in loc 
                    finally: 
                        self.trace("execution finished:", repr(source)[:50]) 
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    excinfo = sys.exc_info()
                    l = traceback.format_exception(*excinfo) 
                    errortext = "".join(l)
                    self._outgoing.put(Message.CHANNEL_CLOSE_ERROR(channel.id, errortext)) 
                    self.trace(errortext) 
                else:
                    self._outgoing.put(Message.CHANNEL_CLOSE(channel.id))
        finally:
            self.trace('leaving %r' % threading.currentThread())

    # _____________________________________________________________________
    #
    # High Level Interface 
    # _____________________________________________________________________
    
    def remote_exec(self, source):
        """ return channel object for communicating with the asynchronously 
            executing 'source' code which will have a corresponding 'channel' 
            object in its executing namespace. 
        """ 
        source = str(Source(source))
        channel = self.channelfactory.new()
        self._outgoing.put(Message.CHANNEL_OPEN(channel.id, source))
        return channel

class Channel(object):
    """Communication channel between two possibly remote threads of code. """
    def __init__(self, gateway, id):
        assert isinstance(id, int)
        self.gateway = gateway
        self.id = id 
        self._items = Queue.Queue()
        self._closeevent = threading.Event()

    def _close(self, error=None):
        if error is not None:
            self._error = RemoteError(error)
            self._items.put(self._error) 
        else:
            self._error = None
        self._closeevent.set()

    def __repr__(self):
        flag = self._closeevent.isSet() and "closed" or "open"
        return "<Channel id=%d %s>" % (self.id, flag)

    def waitclose(self, timeout): 
        """ wait until this channel is closed.  Note that a closed
        channel may still hold items that will be received or 
        send. Note that exceptions from the other side will be 
        reraised as gateway.ExecutionFailed exceptions containing 
        a textual representation of the remote traceback. 
        """
        self._closeevent.wait(timeout=timeout) 
        if not self._closeevent.isSet():
            raise IOError, "Timeout"
        if self._error:
            raise self._error 
        
    def send(self, item): 
        """sends the given item to the other side of the channel, 
        possibly blocking if the sender queue is full. 
        Note that each value V of the items needs to have the
        following property (all basic types in python have it):
        eval(repr(V)) == V."""
        self.gateway._outgoing.put(Message.CHANNEL_DATA(self.id, repr(item)))

    def receive(self):
        """receives an item that was sent from the other side, 
        possibly blocking if there is none. 
        Note that exceptions from the other side will be 
        reraised as gateway.ExecutionFailed exceptions containing 
        a textual representation of the remote traceback. 
        """
        x = self._items.get() 
        if isinstance(x, RemoteError):
            raise x 
        return x

# 
# helpers 
#

class ChannelFactory(object):
    def __init__(self, gateway, startcount=1): 
        self._dict = dict()
        self._lock = threading.RLock()
        self.gateway = gateway
        self.count = startcount

    def new(self): 
        self._lock.acquire()
        try:
            channel = Channel(self.gateway, self.count)
            self._dict[self.count] = channel
            return channel
        finally:
            self.count += 2
            self._lock.release()
        
    def __getitem__(self, key):
        self._lock.acquire()
        try:
            return self._dict[key]
        finally:
            self._lock.release()
    def __setitem__(self, key, value):
        self._lock.acquire()
        try:
            self._dict[key] = value
        finally:
            self._lock.release()
    def __delitem__(self, key):
        self._lock.acquire()
        try:
            del self._dict[key]
        finally:
            self._lock.release()

# ___________________________________________________________________________
#
# Messages 
# ___________________________________________________________________________
# the size of a number on the wire 
numsize = struct.calcsize("!i")
# header of a packet 
# int message_type: 0==exitgateway,         
#                   1==channelfinished_ok,
#                   2==channelfinished_err, 
#                   3==channelopen # executes source code 
#                   4==channelsend # marshals obj
class Message:
    """ encapsulates Messages and their wire protocol. """
    _types = {}
    def __init__(self, channelid=0, data=''): 
        self.channelid = channelid 
        self.data = str(data)
       
    def writeto(self, io):
        data = str(self.data)
        header = struct.pack("!iii", self.msgtype, self.channelid, len(data))
        io.write(header)
        io.write(data) 

    def readfrom(cls, io): 
        header = io.read(numsize*3)  
        msgtype, senderid, stringlen = struct.unpack("!iii", header)
        if stringlen: 
            string = io.read(stringlen)
        else:
            string = '' 
        msg = cls._types[msgtype](senderid, string)
        return msg 
    readfrom = classmethod(readfrom) 

    def post_sent(self, gateway, excinfo=None):
        pass

    def __repr__(self):
        if len(self.data) > 50:
            return "<Message.%s channelid=%d len=%d>" %(self.__class__.__name__, 
                        self.channelid, len(self.data))
        else: 
            return "<Message.%s channelid=%d %r>" %(self.__class__.__name__, 
                        self.channelid, self.data)


def _setupmessages():
    #
    # EXIT_GATEWAY and STOP_RECEIVING are messages to cleanly
    # bring down the IO connection, i.e. it shouldn't die 
    # unexpectedly. 
    #
    # First an EXIT_GATEWAY message is send which results
    # on the other side's receive_handle
    # which cleanly 
    class EXIT_GATEWAY(Message):
        def received(self, gateway):
            gateway._stopexec()
            gateway._outgoing.put(self.STOP_RECEIVING()) 
            raise SystemExit 
        def post_sent(self, gateway, excinfo=None):
            gateway.io.close_write()
            raise SystemExit
    class STOP_RECEIVING(Message):
        def received(self, gateway):
            # note that we don't need to close io.close_read()
            # as the sender side will have closed the io
            # already. With sockets closing it would raise
            # a Transport Not Connected exception
            raise SystemExit 
        def post_sent(self, gateway, excinfo=None):
            gateway.io.close_write()
            raise SystemExit
            
    class CHANNEL_OPEN(Message):
        def received(self, gateway):
            channel = Channel(gateway, self.channelid) 
            gateway.channelfactory[self.channelid] = channel 
            gateway._execqueue.put((channel, self.data)) 
    class CHANNEL_DATA(Message):
        def received(self, gateway):
            channel = gateway.channelfactory[self.channelid]
            channel._items.put(eval(self.data)) 
    class CHANNEL_CLOSE(Message):
        def received(self, gateway):
            channel = gateway.channelfactory[self.channelid]
            channel._close()
            del gateway.channelfactory[channel.id]
    class CHANNEL_CLOSE_ERROR(Message):
        def received(self, gateway):
            channel = gateway.channelfactory[self.channelid]
            channel._close(self.data)
    classes = [x for x in locals().values() if hasattr(x, '__bases__')]
    classes.sort(lambda x,y : cmp(x.__name__, y.__name__))
    i = 0
    for cls in classes: 
        Message._types[i] = cls  
        cls.msgtype = i
        setattr(Message, cls.__name__, cls) 
        i+=1

_setupmessages()

                    
def getid(gw, cache={}):
    name = gw.__class__.__name__ 
    try:
        return cache.setdefault(name, {})[id(gw)]
    except KeyError:
        cache[name][id(gw)] = x = "%s:%s.%d" %(os.getpid(), gw.__class__.__name__, len(cache[name]))
        return x

_gateways = []
def cleanup_atexit():
    print "="*20 + "cleaning up" + "=" * 20
    for x in _gateways: 
        if x.workerthreads:
            x.exit()
