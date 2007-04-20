
""" objkeeper - Storage for remoteprotocol
"""

from types import FunctionType
from distributed import faker

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
        # there are some attributes, which cannot be modified later, nor
        # passed into default values, ignore them
        if key in ('__dict__', '__weakref__', '__class__',
                   '__dict__', '__bases__'):
            return True
        return False
    
    def register_type(self, protocol, tp):
        try:
            return self.exported_types[tp]
        except KeyError:
            self.exported_types[tp] = self.exported_types_id
            self.exported_types_reverse[self.exported_types_id] = tp
            tp_id = self.exported_types_id
            self.exported_types_id += 1

        protocol.send(('type_reg', faker.wrap_type(protocol, tp, tp_id)))
        return tp_id
    
    def fake_remote_type(self, protocol, tp_data):
        type_id, name_, dict_w, bases_w = tp_data
        tp = faker.unwrap_type(self, protocol, type_id, name_, dict_w, bases_w)

    def register_remote_type(self, tp, type_id):
        self.remote_types[type_id] = tp
        self.reverse_remote_types[tp] = type_id
    
    def get_type(self, id):
        return self.remote_types[id]

    def get_object(self, id):
        return self.exported_objects[id]
    
    def register_remote_object(self, controller, id):
        self.remote_objects[controller] = id

    def get_remote_object(self, controller):
        return self.remote_objects[controller]
        
