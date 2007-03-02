
""" objkeeper - Storage for remoteprotocol
"""

# XXX jeez

import sys
try:
    1/0
except:
    _, _, tb = sys.exc_info()
    GetSetDescriptor = type(type(tb).tb_frame)

class RemoteBase(object):
    pass

from types import FunctionType

class ObjKeeper(object):
    def __init__(self, exported_names = {}):
        self.exported_objects = [] # list of object that we've exported outside
        self.exported_names = exported_names # dictionary of visible objects
        self.exported_types = {} # dict of exported types
        self.remote_types = {}
        self.reverse_remote_types = {}
        self.remote_objects = {}
        self.exported_types_id = 0 # unique id of exported types
        self.exported_types_reverse = {} # reverse dict of exported types
    
    def register_object(self, obj):
        # XXX: At some point it makes sense not to export them again and again...
        self.exported_objects.append(obj)
        return len(self.exported_objects) - 1
    
    def ignore(self, key, value):
        if key in ('__dict__', '__weakref__', '__class__'):
            return True
        if isinstance(value, GetSetDescriptor):
            return True
        return False
    
    def register_type(self, protocol, tp):
        try:
            return self.exported_types[tp]
        except KeyError:
            print "Registering type %s as %s" % (tp, self.exported_types_id)
            self.exported_types[tp] = self.exported_types_id
            self.exported_types_reverse[self.exported_types_id] = tp
            tp_id = self.exported_types_id
            self.exported_types_id += 1
        
        # XXX: We don't support inheritance here, nor recursive types
        #      shall we???
        _dict = dict([(key, protocol.wrap(getattr(tp, key))) for key in dir(tp) 
            if not self.ignore(key, getattr(tp, key))])
        protocol.send(("type_reg", (tp_id, 
            tp.__name__, _dict)))
        return tp_id
    
    def fake_remote_type(self, protocol, type_id, _name, _dict):
        print "Faking type %s as %s" % (_name, type_id)
        # create and register new type
        d = dict([(key, None) for key in _dict])
        # some stuff needs to go first...
        if '__doc__' in _dict:
            d['__doc__'] = protocol.unwrap(_dict['__doc__'])
        tp = type(_name, (RemoteBase,), d)
        # Make sure we cannot instantiate the remote type
        self.remote_types[type_id] = tp
        self.reverse_remote_types[tp] = type_id
        for key, value in _dict.items():
            if key != '__doc__':
                v = protocol.unwrap(value)
                if isinstance(v, FunctionType):
                    setattr(tp, key, staticmethod(v))
                else:
                    setattr(tp, key, v)
            #elif key == '__new__':
            #    import pdb
            #    pdb.set_trace()
            #    tp.new = value
                    
    def get_type(self, id):
        return self.remote_types[id]

    def get_object(self, id):
        return self.exported_objects[id]
    
    def register_remote_object(self, controller, id):
        self.remote_objects[controller] = id

    def get_remote_object(self, controller):
        return self.remote_objects[controller]
