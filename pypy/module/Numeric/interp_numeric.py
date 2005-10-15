

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root


class Index(object):
    """Base index class representing either an integer, a slice, an ellipsis"""

class IntIndex(Index):
    def __init__(self, intval ):
        self.index = intval

class SliceIndex(Index):
    def __init__(self, sliceval ):
        self.slice = sliceval

    def indices(self, dim):
        """Returns the size of the slice given the dimension of the array
        it applies to"""
        # probably not RPython
        return self.slice.indices( dim )

        
class EllipsisIndex(Index):
    def __init__(self):
        pass


def get_storage_size( dims ):
    n = 1
    for d in dims:
        n *= d
        assert d>=0
    if n==0:
        return 1
    return n

def is_integer( space, w_obj ):
    return space.is_true(space.isinstance( w_obj, space.w_int ) )

def convert_index_type( space, w_obj ):
    if space.is_true(space.isinstance( w_obj, space.w_int ) ):
        return [ IntIndex( space.int_w(w_obj) ) ], False, False
    if not space.is_true(space.isinstance( w_obj, space.w_tuple )):
        raise OperationError(space.w_IndexError,
                             space.wrap("index must be either an int or a sequence"))
    multi_index = []
    has_slice = False
    has_ellipsis = False
    for w_idx in space.unpackiterable( w_obj ):
        if space.is_true(space.isinstance( w_idx, space.w_int )):
            multi_index.append( IntIndex( space.int_w( w_idx ) ) )
        elif space.is_true(space.isinstance( w_idx, space.w_slice )):
            multi_index.append( SliceIndex( space.unwrap( w_idx ) ) )
            has_slice = True
        elif space.is_w( w_idx, space.w_Ellipsis ):
            multi_index.append( EllipsisIndex() )
            has_ellipsis = True
        else:
            raise OperationError(space.w_IndexError,
                                 space.wrap("each subindex must be either a "
                                            "slice, an integer, Ellipsis, or"
                                            " NewAxis"))
    return multi_index, has_slice, has_ellipsis


class W_Array(Wrappable):

    def __init__(self, space, dims, strides=None ):
        self.space = space
        assert isinstance(dims, list)
        self.dims = dims
        self.strides = [1]
        self.base_offset = 0
        if strides is None:
            stride = 1
            for n in self.dims[:-1]:
                stride *= n
                self.strides.append( stride )
            self.strides.reverse()
        else:
            self.strides=strides

    def check_scalar_index(self, space, w_index):
        if not space.is_true(space.isinstance( w_index, space.w_int )):
            raise NotImplementedError
        idx = space.unwrap( w_index )
        assert isinstance( idx, int )
        return idx

    def descr___getitem__( self, space, w_index ):
        multi_idx, has_slice, has_ellipsis = convert_index_type( space, w_index )
        if not has_slice and not has_ellipsis and len(multi_idx)==len(self.dims):
            idx_tuple = []
            for idx in multi_idx:
                assert isinstance(idx, IntIndex)
                idx_tuple.append(idx.index)
            return self.get_single_item( space, idx_tuple )
        if has_ellipsis:
            # replace ellipsis with slice objects according to array dimensions
            # TODO
            pass
        return self.get_slice( space, multi_idx )

    def descr___setitem__( self, space, w_index, w_value ):
        multi_idx, has_slice, has_ellipsis = convert_index_type( space, w_index )
        if not has_slice and not has_ellipsis and len(multi_idx)==len(self.dims):
            idx_tuple = []
            for idx in multi_idx:
                assert isinstance(idx, IntIndex)
                idx_tuple.append(idx.index)
            return self.set_single_item( space, idx_tuple, w_value )
        if len(multi_idx)<len(self.dims):
            # append full slice objects to complete the dimensions
            pass
        if has_ellipsis:
            # replace ellipsis with slice objects according to array dimensions
            # TODO
            pass
        return self.set_slice( space, multi_idx, w_value )

    def descr_typecode(self,space):
        return self.typecode(space)

    def fget_shape( space, self ):
        return space.newtuple( [ self.space.wrap( i ) for i in self.dims ] )

    def get_array_offset( self, idx_tuple ):
        if len(idx_tuple)>len(self.dims):
            # TODO raise OperationError
            raise RuntimeError
        idx = self.base_offset
        for i in range(len(idx_tuple)):
            idx += self.strides[i]*idx_tuple[i]
        return idx

    def typecode(self,space):
        raise OperationError( space.w_NotImplemented,
                              space.wrap("calling abstract base class" ))


class W_Array_Float(W_Array):

    def __init__(self, space, dims, strides=None, storage=None ):
        W_Array.__init__(self, space, dims, strides )
        self.storage = []
        if storage is not None:
            assert isinstance(storage, list)
            # TODO return proper exception here
            # assert len(storage)==storage_size ### can't check that because of slicing
            assert isinstance(storage[0], float)
            self.storage = storage
        else:
            storage_size = get_storage_size(dims)
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

    def get_slice( self, space, multi_idx ):
        # compute dim of extracted array
        dims = []
        strides = []
        last_stride = 1
        offset = self.base_offset
        for i in range(len(multi_idx)):
            idx = multi_idx[i]
            if isinstance( idx, SliceIndex):
                start, stop, step = idx.indices( self.dims[i] )
                dim = (stop-start)//step
                stride = self.strides[i]*step
                dims.append( dim )
                strides.append( step )
            elif isinstance( idx, IntIndex ):
                offset+= idx.index*self.strides[i]
        array = W_Array_Float( space, dims, strides, self.storage )
        return space.wrap(array)

    def typecode(self,space):
        return space.wrap('d')

class W_Array_Integer(W_Array):

    def __init__(self, space, dims, strides=None, storage=None ):
        W_Array.__init__(self, space, dims, strides )
        self.storage = []
        if storage is not None:
            assert isinstance(storage, list)
            # TODO return proper exception here
            # assert len(storage)==storage_size ### can't check that because of slicing
            assert isinstance(storage[0], int)
            self.storage = storage
        else:
            storage_size = get_storage_size(dims)
            self.storage = [0]*storage_size

    def get_single_item( self, space, idx_tuple ):
        if len(idx_tuple)!=len(self.dims):
            # TODO raise OperationError or remove this and make it a pre-condition
            raise RuntimeError

        idx = self.get_array_offset( idx_tuple )
        return space.wrap( self.storage[idx] )

    def set_single_item( self, space, idx_tuple, w_value ):
        idx = self.get_array_offset( idx_tuple )
        value = space.int_w( w_value )
        self.storage[idx] = value

    def get_slice( self, space, multi_idx ):
        # compute dim of extracted array
        dims = []
        strides = []
        last_stride = 1
        offset = self.base_offset
        for i in range(len(multi_idx)):
            idx = multi_idx[i]
            if isinstance( idx, SliceIndex):
                start, stop, step = idx.indices( self.dims[i] )
                dim = (stop-start)//step
                stride = self.strides[i]*step
                dims.append( dim )
                strides.append( step )
            elif isinstance( idx, IntIndex ):
                offset+= idx.index*self.strides[i]
        array = W_Array_Float( space, dims, strides, self.storage )
        return space.wrap(array)

    def typecode(self,space):
        return space.wrap('l')


descr___getitem__ = interp2app( W_Array.descr___getitem__, unwrap_spec=['self', ObjSpace, W_Root ] )
descr___setitem__ = interp2app( W_Array.descr___setitem__, unwrap_spec=['self', ObjSpace, W_Root, W_Root ] )
descr_typecode = interp2app( W_Array.descr_typecode, unwrap_spec=['self', ObjSpace ] )

W_Array.typedef = TypeDef("array",
                          shape = GetSetProperty( W_Array.fget_shape, cls=W_Array),
                          __getitem__ = descr___getitem__,
                          __setitem__ = descr___setitem__,
                          typecode = descr_typecode,
                          )

#W_Array_Float.typedef = TypeDef("array", W_Array.typedef,)
#W_Array_Integer.typedef = TypeDef("array", W_Array.typedef, )


def w_zeros( space, w_dim_tuple, type_str ):
    dims = []
    for w_int in space.unpackiterable(w_dim_tuple):
        dims.append( space.unwrap( w_int ) )
    if type_str == 'd':
        return space.wrap(W_Array_Float( space, dims ))
    raise OperationError( space.w_ValueError, space.wrap('Unknown type code') )

w_zeros.unwrap_spec = [ ObjSpace, W_Root, str ]


TOWER_TYPES_VALUES=[(int,1),(float,1.0),(complex,2.0+3j)] #we will work with these types to start with
TOWER_TYPES_VALUES=TOWER_TYPES_VALUES[0:2]   #cannot unpack complex values yet at interp level.

TOWER_TYPES=[typ for typ,val in TOWER_TYPES_VALUES]



def OpError(space,w_arg):
    raise OperationError( space.w_TypeError,space.wrap('Cannot unwrap this <%s>'%str(w_arg)))


def int_array_from_iterable( space, w_it ):
    N = space.int_w(space.len( w_it ))
    storage = N*[0]
    i = 0
    for w_obj in space.unpackiterable( w_it ):
        storage[i] = space.int_w( w_it )
        i+=1

def float_array_from_iterable( space, w_it ):
    N = space.int_w(space.len( w_it ))
    storage = N*[0.]
    i = 0
    for w_obj in space.unpackiterable( w_it ):
        storage[i] = space.float_w( w_it )
        i+=1

def array( space, w_arg):
    TYPES = "ldD"
    if (space.is_true( space.isinstance( w_arg, space.w_list ) ) or
        space.is_true( space.isinstance( w_arg, space.w_tuple ) ) ):
        if not space.is_true( w_arg ):
            return W_Array_Integer(space,[0,])
        ty = -1
        for w_obj in space.unpackiterable( w_arg ):
            if ty< 0 and space.is_true( space.isinstance( w_arg, space.w_int ) ):
                ty = 0
            if ty< 1 and space.is_true( space.isinstance( w_arg, space.w_float ) ):
                ty = 1
##             elif ty<2 and space.is_true( space.isinstance( w_arg, space.w_complex ) ):
##                 ty = 2
            else:
                raise OperationError( space.w_TypeError,
                                      space.wrap("Only int, float and complex currently supported") )
            if ty == 2:
                break
        if ty==0:
            return int_array_from_iterable( space, w_arg )
        elif ty==1:
            return float_array_from_iterable( space, w_arg )
        elif ty==2:
            raise OperationError( space.w_NotImplementedError,
                                  space.wrap("complex array not implemented") )
        else:
            raise OperationError( space.w_TypeError,
                                  space.wrap("Unknown array type") )
            
    elif space.is_true( space.isinstance( w_arg, space.w_int ) ):
        ivalue = space.int_w( w_arg )
        return W_Array_Integer(space, [], storage=[ivalue])
    elif space.is_true( space.isinstance( w_arg, space.w_float ) ):
        fvalue = space.float_w( w_arg )
        return W_Array_Float(space, [], storage=[fvalue])
    else:
        OpError(space,w_arg)
        

array.unwrap_spec = [ ObjSpace, W_Root ]

