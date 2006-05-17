from pypy.rpython.lltypesystem import lltype, llmemory

import struct

primitive_to_fmt = {lltype.Signed:          "l",
                    lltype.Unsigned:        "L",
                    lltype.Char:            "c",
                    lltype.Bool:            "B",
                    lltype.Float:           "d",
                    llmemory.Address:       "P",
                    }


#___________________________________________________________________________
# Utility functions that know about the memory layout of the lltypes
# in the simulation

#returns some sort of layout information that is useful for the simulatorptr
def get_layout(TYPE):
    layout = {}
    if isinstance(TYPE, lltype.Primitive):
        return primitive_to_fmt[TYPE]
    elif isinstance(TYPE, lltype.Ptr):
        return "P"
    elif isinstance(TYPE, lltype.Struct):
        curr = 0
        for name in TYPE._names:
            layout[name] = curr
            curr += get_fixed_size(TYPE._flds[name])
        layout["_size"] = curr
        return layout
    elif isinstance(TYPE, lltype.Array):
        return (get_fixed_size(lltype.Signed), get_fixed_size(TYPE.OF))
    elif isinstance(TYPE, lltype.OpaqueType):
        return "i"
    elif isinstance(TYPE, lltype.FuncType):
        return "i"
    elif isinstance(TYPE, lltype.PyObjectType):
        return "i"
    else:
        assert 0, "type %s not yet implemented" % (TYPE, )

def get_fixed_size(TYPE):
    if isinstance(TYPE, lltype.Primitive):
        if TYPE == lltype.Void:
            return 0
        return struct.calcsize(primitive_to_fmt[TYPE])
    elif isinstance(TYPE, lltype.Ptr):
        return struct.calcsize("P")
    elif isinstance(TYPE, lltype.Struct):
        return get_layout(TYPE)["_size"]
    elif isinstance(TYPE, lltype.Array):
        return get_fixed_size(lltype.Unsigned)
    elif isinstance(TYPE, lltype.OpaqueType):
        return get_fixed_size(lltype.Unsigned)
    elif isinstance(TYPE, lltype.FuncType):
        return get_fixed_size(lltype.Unsigned)
    elif isinstance(TYPE, lltype.PyObjectType):
        return get_fixed_size(lltype.Unsigned)
    assert 0, "not yet implemented"

def get_variable_size(TYPE):
    if isinstance(TYPE, lltype.Array):
        return get_fixed_size(TYPE.OF)
    elif isinstance(TYPE, lltype.Primitive):
        return 0
    elif isinstance(TYPE, lltype.Struct):
        if TYPE._arrayfld is not None:
            return get_variable_size(TYPE._flds[TYPE._arrayfld])
        else:
            return 0
    elif isinstance(TYPE, lltype.OpaqueType):
        return 0
    elif isinstance(TYPE, lltype.FuncType):
        return 0
    elif isinstance(TYPE, lltype.PyObjectType):
        return 0
    elif isinstance(TYPE, lltype.Ptr):
        return 0
    else:
        assert 0, "not yet implemented"

def sizeof(TYPE, i=None):
    fixedsize = get_fixed_size(TYPE)
    varsize = get_variable_size(TYPE)
    if i is None:
        assert varsize == 0
        return fixedsize
    else:
        return fixedsize + i * varsize

def convert_offset_to_int(offset):
    if isinstance(offset, llmemory.FieldOffset):
        layout = get_layout(offset.TYPE)
        return layout[offset.fldname]
    elif isinstance(offset, llmemory.CompositeOffset):
        return sum([convert_offset_to_int(item) for item in offset.offsets])
    elif type(offset) == llmemory.AddressOffset:
        return 0
    elif isinstance(offset, llmemory.ItemOffset):
        return sizeof(offset.TYPE) * offset.repeat
    elif isinstance(offset, llmemory.ArrayItemsOffset):
        return get_fixed_size(lltype.Signed)
    elif isinstance(offset, llmemory.GCHeaderOffset):
        return sizeof(offset.gcheaderbuilder.HDR)
    else:
        raise Exception("unknown offset type %r"%offset)
        
# _____________________________________________________________________________
# the following functions are used to find contained pointers


def offsets_to_gc_pointers(TYPE):
    if isinstance(TYPE, lltype.Struct):
        offsets = []
        for name in TYPE._names:
            FIELD = getattr(TYPE, name)
            if (isinstance(FIELD, lltype.Ptr) and FIELD._needsgc() and
                FIELD.TO is not lltype.PyObject):
                offsets.append(llmemory.offsetof(TYPE, name))
            elif isinstance(FIELD, lltype.Struct):
                suboffsets = offsets_to_gc_pointers(FIELD)
                offsets += [s + llmemory.offsetof(TYPE, name) for s in suboffsets]
        return offsets
    return []

def varsize_offset_to_length(TYPE):
    if isinstance(TYPE, lltype.Array):
        return 0
    elif isinstance(TYPE, lltype.Struct):
        layout = get_layout(TYPE)
        return layout[TYPE._arrayfld]

def varsize_offsets_to_gcpointers_in_var_part(TYPE):
    if isinstance(TYPE, lltype.Array):
        if isinstance(TYPE.OF, lltype.Ptr):
            return [0]
        elif isinstance(TYPE.OF, lltype.Struct):
            return offsets_to_gc_pointers(TYPE.OF)
        return []
    elif isinstance(TYPE, lltype.Struct):
        return varsize_offsets_to_gcpointers_in_var_part(getattr(TYPE,
                                                                 TYPE._arrayfld)) 
    
