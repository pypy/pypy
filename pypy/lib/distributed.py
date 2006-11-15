
""" Distributed controller(s) for use with transparent proxy objects

First idea:

1. We use py.execnet to create a connection to wherever
2. We run some code there (RSync in advance makes some sense)
3. We access remote objects like normal ones, with a special protocol

Local side:
  - Request an object from remote side from global namespace as simple
    --- request(name) --->
  - Receive an object which is in protocol described below which is
    constructed as shallow copy of the remote type.

    Shallow copy is defined as follows:

    - for interp-level object that we know we can provide transparent proxy
      we just do that

    - for others we fake or fail depending on object

    - for user objects, we create a class which fakes all attributes of
      a class as transparent proxies of remote objects, we create an instance
      of that class and populate __dict__

    - for immutable types, we just copy that

Remote side:
  - we run code, whatever we like
  - additionally, we've got thread exporting stuff (or just exporting
    globals, whatever)
  - for every object, we just send an object, or provide a protocol for
    sending it in a different way.

"""

try:
    from pypymagic import transparent_proxy as proxy
except ImportError:
    raise ImportError("Cannot work without transparent proxy functional")

# XXX We do not make any garbage collection. We'll need it at some point

from pypymagic import pypy_repr

import types
from marshal import dumps

class AbstractProtocol(object):
    letter_types = {
        'l' : list,
        'd' : dict,
        't' : tuple,
        'i' : int,
        'f' : float,
        'u' : unicode,
        'l' : long,
        's' : str,
        'lst' : list,
        'fun' : types.FunctionType
    }
    type_letters = dict([(value, key) for key, value in letter_types.items()])
    assert len(type_letters) == len(letter_types)
    
    def __init__(self):
        self.objs = [] # we just store everything, maybe later
           # we'll need some kind of garbage collection
    
    def register_obj(self, obj):
        self.objs.append(obj)
        return len(self.objs) - 1

    def wrap(self, obj):
        """ Wrap an object as sth prepared for sending
        """
        tp = type(obj)
        if tp in (str, int, float, long, unicode):
            # simple, immutable object, just copy
            return (self.type_letters[tp], obj)
        elif tp is tuple:
            # we just pack all of the items
            return ('t', tuple([self.wrap(elem) for elem in obj]))
        elif tp in (list, dict, types.FunctionType):
            id = self.register_obj(obj)
            return (self.type_letters[tp], id)
        else:
            raise NotImplementedError("Cannot wrap %s: unsupported type %s" %
                (obj, tp))
    
    def unwrap(self, data):
        """ Unwrap an object
        """
        tp_letter, obj_data = data
        tp = self.letter_types[tp_letter]
        if tp in (str, int, float, long, unicode):
            return obj_data # this is the object
        elif tp is tuple:
            return tuple([self.unwrap(i) for i in obj_data])
        elif tp in (list, dict, types.FunctionType):
            return proxy(tp, RemoteObject(self, obj_data).perform)
        else:
            raise NotImplementedError("Cannot unwrap %s" % (data,))
    
    def perform(self, *args, **kwargs):
        raise NotImplementedError("Abstract only protocol")
    
    # some simple wrappers
    def pack_args(self, args, kwargs):
        args = [self.wrap(i) for i in args]
        kwargs = dict([(self.wrap(key), self.wrap(val)) for key, val in kwargs.items()])
        return args, kwargs
    
    def unpack_args(self, args, kwargs):
        args = [self.unwrap(i) for i in args]
        kwargs = dict([(self.unwrap(key), self.unwrap(val)) for key, val in kwargs.items()])
        return args, kwargs

class LocalProtocol(AbstractProtocol):
    """ This is stupid protocol for testing purposes only
    """
    def perform(self, id, name, *args, **kwargs):
        obj = self.objs[id]
        # we pack and than unpack, for tests
        args, kwargs = self.pack_args(args, kwargs)
        assert isinstance(name, str)
        dumps((args, kwargs))
        args, kwargs = self.unpack_args(args, kwargs)
        return getattr(obj, name)(*args, **kwargs)

def remote_loop(send, receive, protocol=None):
    # the simplest version possible, without any concurrency and such
    if protocol is None:
        protocol = RemoteProtocol(send, receive, {})
    wrap = protocol.wrap
    unwrap = protocol.unwrap
    # we need this for wrap/unwrap
    while 1:
        command, data = receive()
        if command == 'get':
            # XXX: Error recovery anyone???
            send(wrap(protocol.exported_names[data]))
        elif command == 'call':
            id, name, args, kwargs = data
            args, kwargs = unpack_args(args, kwargs)
            assert not 'Transparent' in pypy_repr(protocol.objs[id])
            retval = getattr(protocol.objs[id], name)(args, kwargs)
            send(("finished", wrap(retval)))
        elif command == 'finished':
            return unwrap(data)
        else:
            raise NotImplementedError("command %s" % command)

class RemoteProtocol(AbstractProtocol):
    #def __init__(self, gateway, remote_code):
    #    self.gateway = gateway
    def __init__(self, send, receive, exported_names={}):
        self.exported_names = exported_names
        self.send = send
        self.receive = receive
        self.objs = []
    
    def perform(self, id, name, *args, **kwargs):
        args, kwargs = self.pack_args(args, kwargs)
        self.send(('call', (id, name, args, kwargs)))
        retval = remote_loop(self.send, self.receive, self)
        return retval
    
    def get_remote(self, name):
        self.send(("get", name))
        return self.unwrap(self.receive())

class RemoteObject(object):
    def __init__(self, protocol, id):
        self.id = id
        self.protocol = protocol
    
    def perform(self, name, *args, **kwargs):
        return self.protocol.perform(self.id, name, *args, **kwargs)

def bootstrap(gw):
    import py
    import sys
    return gw.remote_exec(py.code.Source(sys.modules[__name__], "remote_loop(channel.send, channel.receive)"))


##class RemoteFunction(object):
##    def __init__(self, channel, name):
##        channel.send(protocol.get(name))
##        self.channel = channel
##        self.id = protocol.id(channel.receive())
##        self.fun = proxy(types.FunctionType, self.perform)
##    
##    def perform(self, name, *args, **kwargs):
##        self.channel.send(protocol.pack_call(self.id, name, args, kwargs))
##        return protocol.unpack(self.channel.receive())
