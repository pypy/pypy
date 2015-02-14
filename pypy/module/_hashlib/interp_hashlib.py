from __future__ import with_statement

from rpython.rlib import rgc, ropenssl
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.tool.sourcetools import func_renamer

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.module.thread.os_lock import Lock


algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

def hash_name_mapper_callback(obj_name, userdata):
    state = global_state[0]
    assert state is not None
    if not obj_name:
        return
    # Ignore aliased names, they pollute the list and OpenSSL appears
    # to have a its own definition of alias as the resulting list
    # still contains duplicate and alternate names for several
    # algorithms.
    if obj_name[0].c_alias:
        return
    try:
        w_name = state.space.wrap(rffi.charp2str(obj_name[0].c_name))
        state.space.call_method(state.w_meth_names, "add", w_name)
    except OperationError, e:
        state.w_error = e

# XXX make it threadlocal?
global_state = [None]

class State:
    def __init__(self, space):
        self.space = space
        self.generate_method_names(space)

    def generate_method_names(self, space):
        if not we_are_translated():
            ropenssl.init_digests()
        self.w_error = None
        try:
            global_state[0] = self
            self.w_meth_names = space.call_function(space.w_set)
            ropenssl.OBJ_NAME_do_all(
                ropenssl.OBJ_NAME_TYPE_MD_METH,
                hash_name_mapper_callback, None)
        finally:
            global_state[0] = None
        if self.w_error:
            raise self.w_error

def get(space):
    return space.fromcache(State)

class W_Hash(W_Root):
    NULL_CTX = lltype.nullptr(ropenssl.EVP_MD_CTX.TO)
    ctx = NULL_CTX

    def __init__(self, space, name, copy_from=NULL_CTX):
        self.name = name
        digest_type = self.digest_type_by_name(space)
        self.digest_size = rffi.getintfield(digest_type, 'c_md_size')

        # Allocate a lock for each HASH object.
        # An optimization would be to not release the GIL on small requests,
        # and use a custom lock only when needed.
        self.lock = Lock(space)

        ctx = lltype.malloc(ropenssl.EVP_MD_CTX.TO, flavor='raw')
        rgc.add_memory_pressure(ropenssl.HASH_MALLOC_SIZE + self.digest_size)
        try:
            if copy_from:
                ropenssl.EVP_MD_CTX_copy(ctx, copy_from)
            else:
                ropenssl.EVP_DigestInit(ctx, digest_type)
            self.ctx = ctx
        except:
            lltype.free(ctx, flavor='raw')
            raise

    def __del__(self):
        if self.ctx:
            ropenssl.EVP_MD_CTX_cleanup(self.ctx)
            lltype.free(self.ctx, flavor='raw')

    def digest_type_by_name(self, space):
        digest_type = ropenssl.EVP_get_digestbyname(self.name)
        if not digest_type:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unknown hash function"))
        return digest_type

    def descr_repr(self, space):
        addrstring = self.getaddrstring(space)
        return space.wrap("<%s HASH object at 0x%s>" % (
            self.name, addrstring))

    @unwrap_spec(string='bufferstr')
    def update(self, space, string):
        with rffi.scoped_nonmovingbuffer(string) as buf:
            with self.lock:
                # XXX try to not release the GIL for small requests
                ropenssl.EVP_DigestUpdate(self.ctx, buf, len(string))

    def copy(self, space):
        "Return a copy of the hash object."
        with self.lock:
            return W_Hash(space, self.name, copy_from=self.ctx)

    def digest(self, space):
        "Return the digest value as a string of binary data."
        digest = self._digest(space)
        return space.wrap(digest)

    def hexdigest(self, space):
        "Return the digest value as a string of hexadecimal digits."
        digest = self._digest(space)
        hexdigits = '0123456789abcdef'
        result = StringBuilder(self.digest_size * 2)
        for c in digest:
            result.append(hexdigits[(ord(c) >> 4) & 0xf])
            result.append(hexdigits[ ord(c)       & 0xf])
        return space.wrap(result.build())

    def get_digest_size(self, space):
        return space.wrap(self.digest_size)

    def get_block_size(self, space):
        digest_type = self.digest_type_by_name(space)
        block_size = rffi.getintfield(digest_type, 'c_block_size')
        return space.wrap(block_size)

    def get_name(self, space):
        return space.wrap(self.name)

    def _digest(self, space):
        with lltype.scoped_alloc(ropenssl.EVP_MD_CTX.TO) as ctx:
            with self.lock:
                ropenssl.EVP_MD_CTX_copy(ctx, self.ctx)
            digest_size = self.digest_size
            with lltype.scoped_alloc(rffi.CCHARP.TO, digest_size) as digest:
                ropenssl.EVP_DigestFinal(ctx, digest, None)
                ropenssl.EVP_MD_CTX_cleanup(ctx)
                return rffi.charpsize2str(digest, digest_size)


W_Hash.typedef = TypeDef(
    'HASH',
    __repr__=interp2app(W_Hash.descr_repr),
    update=interp2app(W_Hash.update),
    copy=interp2app(W_Hash.copy),
    digest=interp2app(W_Hash.digest),
    hexdigest=interp2app(W_Hash.hexdigest),
    #
    digest_size=GetSetProperty(W_Hash.get_digest_size),
    digestsize=GetSetProperty(W_Hash.get_digest_size),
    block_size=GetSetProperty(W_Hash.get_block_size),
    name=GetSetProperty(W_Hash.get_name),
)
W_Hash.acceptable_as_base_class = False

@unwrap_spec(name=str, string='bufferstr')
def new(space, name, string=''):
    w_hash = W_Hash(space, name)
    w_hash.update(space, string)
    return space.wrap(w_hash)

# shortcut functions
def make_new_hash(name, funcname):
    @func_renamer(funcname)
    @unwrap_spec(string='bufferstr')
    def new_hash(space, string=''):
        return new(space, name, string)
    return new_hash

for _name in algorithms:
    _newname = 'new_%s' % (_name,)
    globals()[_newname] = make_new_hash(_name, _newname)
