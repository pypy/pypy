

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root



def get_storage_size( dims ):
    n = 1
    for d in dims:
        n *= d
        assert d>0
    return d

class W_Array(Wrappable):

    def __init__(self, space, dims ):
        self.space = space
        assert isinstance(dims, list)
        self.dims = dims
        self.strides = [1]
        self.base_object = None
        self.base_offset = 0 # needed later for offseting into a shared storage
        stride = 1
        for n in self.dims[:-1]:
            stride *= n
            self.strides.append( stride )
        self.strides.reverse()

    def check_space_true(self, space, w_index):
        if not space.is_true(space.isinstance( w_index, space.w_int )):
            raise NotImplementedError
        idx = space.unwrap( w_index )
        assert isinstance( idx, int )
        return idx

    def descr___getitem__( self, space, w_index ):
        return self.get_single_item( space, [ self.check_space_true( space, w_index)])

    def descr___setitem__( self, space, w_index, w_value ):
        return self.set_single_item( space, [ self.check_space_true( space, w_index) ], w_value )

    def fget_shape( space, self ):
        return space.newtuple( [ self.space.wrap( i ) for i in self.dims ] )

    def fset_shape( space, self, w_tuple ):
        pass

    def get_array_offset( self, idx_tuple ):
        if len(idx_tuple)>len(self.dims):
            # TODO raise OperationError
            raise RuntimeError
        idx = 0
        for i in range(len(idx_tuple)):
            idx += self.strides[i]*idx_tuple[i]
        return idx


class W_Array_Float(W_Array):

    def __init__(self, space, dims, storage=None ):
        W_Array.__init__(self, space, dims )
        storage_size = get_storage_size(dims)
        self.storage = []
        if storage is not None:
            assert isinstance(storage, list)
            # TODO return proper exception here
            assert len(storage)==storage_size
            assert isinstance(storage[0], float)
            self.storage = storage
        else:
            self.storage = [0.0]*storage_size

    def get_single_item( self, space, idx_tuple ):
        if len(idx_tuple)!=len(self.dims):
            # TODO raise OperationError or remove this and make it a pre-condition
            raise RuntimeError
        idx = self.get_array_offset( idx_tuple )
        return space.wrap( self.storage[idx] )

    def set_single_item( self, space, idx_tuple, w_value ):
        idx = self.get_array_offset( idx_tuple )
        value = space.float_w( w_value )
        self.storage[idx] = value

descr___getitem__ = interp2app( W_Array.descr___getitem__, unwrap_spec=['self', ObjSpace, W_Root ] )
descr___setitem__ = interp2app( W_Array.descr___setitem__, unwrap_spec=['self', ObjSpace, W_Root, W_Root ] )

#get_shape = GetProperty( W_Array_Float.

W_Array.typedef = TypeDef("W_Array",
                          shape = GetSetProperty( W_Array.fget_shape, cls=W_Array),
                          __getitem__ = descr___getitem__,
                          __setitem__ = descr___setitem__,
                          )

W_Array_Float.typedef = TypeDef("W_Array_Float", W_Array.typedef,
                                )

def w_zeros( space, w_dim_tuple, type_str ):
    dims = []
    for w_int in space.unpackiterable(w_dim_tuple):
        dims.append( space.unwrap( w_int ) )
    if type_str == 'd':
        return space.wrap(W_Array_Float( space, dims ))
    raise OperationError( space.w_ValueError, space.wrap('Unknown type code') )

w_zeros.unwrap_spec = [ ObjSpace, W_Root, str ]


"""
"""
class W_NumericArray(Wrappable):

    def __init__(self, space, dims ):
        self.space = space
        assert isinstance(dims, list)
        self.dims = dims
        self.strides = [1]
        self.base_object = None
        self.base_offset = 0 # needed later for offseting into a shared storage
        stride = 1
        for n in self.dims[:-1]:
            stride *= n
            self.strides.append( stride )
        self.strides.reverse()

    def check_space_true(self, space, w_index):
        if not space.is_true(space.isinstance( w_index, space.w_int )):
            raise NotImplementedError
        idx = space.unwrap( w_index )
        assert isinstance( idx, int )
        return idx

    def descr___getitem__( self, space, w_index ):
        return self.get_single_item( space, [ self.check_space_true( space, w_index)])

    def descr___setitem__( self, space, w_index, w_value ):
        return self.set_single_item( space, [ self.check_space_true( space, w_index) ], w_value )

    def fget_shape( space, self ):
        return space.newtuple( [ self.space.wrap( i ) for i in self.dims ] )

    def fset_shape( space, self, w_tuple ):
        pass

    def get_array_offset( self, idx_tuple ):
        if len(idx_tuple)>len(self.dims):
            # TODO raise OperationError
            raise RuntimeError
        idx = 0
        for i in range(len(idx_tuple)):
            idx += self.strides[i]*idx_tuple[i]
        return idx


class W_NumericArray_Float(W_NumericArray):

    def __init__(self, space, dims, storage=None ):
        W_NumericArray.__init__(self, space, dims )
        storage_size = get_storage_size(dims)
        self.storage = []
        if storage is not None:
            assert isinstance(storage, list)
            # TODO return proper exception here
            assert len(storage)==storage_size
            assert isinstance(storage[0], float)
            self.storage = storage
        else:
            self.storage = [0.0]*storage_size

    def get_single_item( self, space, idx_tuple ):
        if len(idx_tuple)!=len(self.dims):
            # TODO raise OperationError or remove this and make it a pre-condition
            raise RuntimeError
        idx = self.get_array_offset( idx_tuple )
        return space.wrap( self.storage[idx] )

    def set_single_item( self, space, idx_tuple, w_value ):
        idx = self.get_array_offset( idx_tuple )
        value = space.float_w( w_value )
        self.storage[idx] = value

descr___getitem__ = interp2app( W_NumericArray.descr___getitem__, unwrap_spec=['self', ObjSpace, W_Root ] )
descr___setitem__ = interp2app( W_NumericArray.descr___setitem__, unwrap_spec=['self', ObjSpace, W_Root, W_Root ] )


W_NumericArray.typedef = TypeDef("W_NumericArray",
                          shape = GetSetProperty( W_NumericArray.fget_shape, cls=W_NumericArray),
                          __getitem__ = descr___getitem__,
                          __setitem__ = descr___setitem__,
                          )

W_NumericArray_Float.typedef = TypeDef("W_NumericArray_Float", W_NumericArray.typedef,
                                )

def w_nzeros( space, w_dim_tuple, type_str ):
    dims = []
    for w_int in space.unpackiterable(w_dim_tuple):
        dims.append( space.unwrap( w_int ) )
    if type_str == 'd':
        return space.wrap(W_NumericArray_Float( space, dims ))
    raise OperationError( space.w_ValueError, space.wrap('Unknown type code') )

w_nzeros.unwrap_spec = [ ObjSpace, W_Root, str ]


def w_array( space, w_dim_tuple):
    raise OperationError( space.w_ValueError, space.wrap('Cannot create void array'))

w_array.unwrap_spec = [ ObjSpace, W_Root ]

