from rpython.flowspace.model import Constant, Variable

def is_immutable(op):
    if op.opname in ('getfield', 'setfield'):
        STRUCT = op.args[0].concretetype.TO
        return STRUCT._immutable_field(op.args[1].value)
    if op.opname in ('getarrayitem', 'setarrayitem'):
        ARRAY = op.args[0].concretetype.TO
        return ARRAY._immutable_field()
    if op.opname == 'getinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:]))
    if op.opname == 'setinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:-1]))
    if op.opname == 'raw_load':
        return len(op.args) >= 3 and bool(op.args[2].value)
    if op.opname == 'raw_store':
        return False
    if op.opname == 'gc_load_indexed':
        T = op.args[0].concretetype.TO
        # XXX: unfortunately, we lost the information about immutability
        # of the inline-array that we are going to access here.
        # E.g., if arg0 is a str, we probably index into the immutable
        # 'chars' field, but it's hard to know.
        return T._hints.get('immutable', False)
    raise AssertionError(op)

def unwraplist(list_v):
    for v in list_v:
        if isinstance(v, Constant):
            yield v.value
        elif isinstance(v, Variable):
            yield None    # unknown
        else:
            raise AssertionError(v)
