from pypy.rpython.lltypesystem import lltype, llmemory

STORAGE_TYPES = [llmemory.Address,
                 lltype.Signed,
                 lltype.Float,
                 lltype.SignedLongLong]
STORAGE_FIELDS = ['addr',
                  'long',
                  'float',
                  'longlong']

def storage_type(T):
    """Return the type used to save values of this type
    """
    if T is lltype.Void:
        return None
    elif T is lltype.Float:
        return 2
    elif T in [lltype.SignedLongLong, lltype.UnsignedLongLong]:
        return 3
    elif T is llmemory.Address or isinstance(T, lltype.Ptr):
        return 0
    elif isinstance(T, lltype.Primitive):
        return 1
    else:
        raise Exception("don't know about %r" % (T,))

state_header = lltype.Struct('state_header',
                             ('f_back', lltype.Ptr(lltype.ForwardReference())),
                             ('signed', lltype.Signed))
state_header.f_back.TO.become(state_header)

class StacklessTransfomer(object):
    def __init__(self, translator):
        self.translator = translator
        
        self.frametypes = {}

    def frame_type_for_vars(self, vars):
        types = [storage_type(v.concretetype) for v in vars]
        counts = dict.fromkeys(range(len(STORAGE_TYPES)), 0)
        for t in types:
            counts[t] = counts[t] + 1
        keys = counts.keys()
        keys.sort()
        key = tuple([counts[k] for k in keys])
        if key in self.frametypes:
            return self.frametypes[key]
        else:
            fields = []
            for i, k in enumerate(key):
                for j in range(k):
                    fields.append(('state_%s_%d'%(STORAGE_FIELDS[i], j), STORAGE_TYPES[i]))
            T = lltype.Struct("state_%d_%d_%d_%d"%tuple(key),
                              ('header', state_header),
                              *fields)
            self.frametypes[key] = T
            return T
            

