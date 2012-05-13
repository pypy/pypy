import py
from pypy.rpython.lltypesystem import lltype, llmemory, llarena, llgroup, rffi
from pypy.rpython.memory.gc.stmgc import StmGC, WORD
from pypy.rpython.memory.gc.stmgc import GCFLAG_GLOBAL, GCFLAG_WAS_COPIED
from pypy.rpython.memory.gc.stmgc import GCFLAG_VISITED
from pypy.rpython.memory.support import mangle_hash


S = lltype.GcStruct('S', ('a', lltype.Signed), ('b', lltype.Signed),
                         ('c', lltype.Signed))
ofs_a = llmemory.offsetof(S, 'a')

SR = lltype.GcForwardReference()
SR.become(lltype.GcStruct('SR', ('s1', lltype.Ptr(S)),
                                ('sr2', lltype.Ptr(SR)),
                                ('sr3', lltype.Ptr(SR))))

WR = lltype.GcStruct('WeakRef', ('wadr', llmemory.Address))
SWR = lltype.GcStruct('SWR', ('wr', lltype.Ptr(WR)))


class FakeStmOperations:
    # The point of this class is to make sure about the distinction between
    # RPython code in the GC versus C code in translator/stm/src_stm.  This
    # class contains a fake implementation of what should be in C.  So almost
    # any use of 'self._gc' is wrong here: it's stmgc.py that should call
    # et.c, and not the other way around.

    PRIMITIVE_SIZES = {1: lltype.Char,
                       WORD: lltype.Signed}
    CALLBACK_ENUM = lltype.Ptr(lltype.FuncType([llmemory.Address] * 3,
                                               lltype.Void))
    GETSIZE  = lltype.Ptr(lltype.FuncType([llmemory.Address], lltype.Signed))

    threadnum = 0          # 0 = main thread; 1,2,3... = transactional threads

    def descriptor_init(self):
        self._in_transaction = False

    def begin_inevitable_transaction(self):
        assert self._in_transaction is False
        self._in_transaction = True

    def commit_transaction(self):
        assert self._in_transaction is True
        self._in_transaction = False

    def in_transaction(self):
        return self._in_transaction

    def set_tls(self, tls):
        assert lltype.typeOf(tls) == llmemory.Address
        assert tls
        if self.threadnum == 0:
            assert not hasattr(self, '_tls_dict')
            self._tls_dict = {0: tls}
            self._tldicts = {0: {}}
            self._transactional_copies = []
        else:
            self._tls_dict[self.threadnum] = tls
            self._tldicts[self.threadnum] = {}

    def get_tls(self):
        return self._tls_dict[self.threadnum]

    def del_tls(self):
        del self._tls_dict[self.threadnum]
        del self._tldicts[self.threadnum]

    def tldict_lookup(self, obj):
        assert lltype.typeOf(obj) == llmemory.Address
        assert obj
        tldict = self._tldicts[self.threadnum]
        return tldict.get(obj, llmemory.NULL)

    def tldict_add(self, obj, localobj):
        assert lltype.typeOf(obj) == llmemory.Address
        assert lltype.typeOf(localobj) == llmemory.Address
        tldict = self._tldicts[self.threadnum]
        assert obj not in tldict
        tldict[obj] = localobj

    def tldict_enum(self):
        from pypy.rpython.memory.gc.stmtls import StmGCTLS
        callback = StmGCTLS._stm_enum_callback
        tls = self.get_tls()
        for key, value in self._tldicts[self.threadnum].iteritems():
            callback(tls, key, value)

    def read_attribute(self, obj, name):
        obj = llmemory.cast_ptr_to_adr(obj)
        hdr = self._gc.header(obj)
        localobj = self.tldict_lookup(obj)
        if localobj == llmemory.NULL:
            localobj = obj
        else:
            assert hdr.tid & GCFLAG_GLOBAL != 0
        localobj = llmemory.cast_adr_to_ptr(localobj, lltype.Ptr(SR))
        return getattr(localobj, name)

    def stm_copy_transactional_to_raw(self, srcobj, dstobj, size):
        llmemory.raw_memcopy(srcobj, dstobj, size)
        self._transactional_copies.append((srcobj, dstobj))


def fake_get_size(obj):
    TYPE = obj.ptr._TYPE.TO
    if isinstance(TYPE, lltype.GcStruct):
        return llmemory.sizeof(TYPE)
    else:
        assert 0

def fake_trace(obj, callback, arg):
    TYPE = obj.ptr._TYPE.TO
    if TYPE == S:
        ofslist = []     # no pointers in S
    elif TYPE == SR:
        ofslist = [llmemory.offsetof(SR, 's1'),
                   llmemory.offsetof(SR, 'sr2'),
                   llmemory.offsetof(SR, 'sr3')]
    elif TYPE == WR:
        ofslist = []
    elif TYPE == SWR:
        ofslist = [llmemory.offsetof(SWR, 'wr')]
    else:
        assert 0
    for ofs in ofslist:
        addr = obj + ofs
        if addr.address[0]:
            callback(addr, arg)

def fake_weakpointer_offset(tid):
    if tid == 124:
        return llmemory.offsetof(WR, 'wadr')
    else:
        return -1

class FakeRootWalker:
    def walk_current_stack_roots(self, *args):
        pass     # no stack roots in this test file
    def walk_current_nongc_roots(self, *args):
        pass     # no nongc roots in this test file


class StmGCTests:
    GCClass = StmGC

    def setup_method(self, meth):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True).translation
        self.gc = self.GCClass(config, FakeStmOperations(),
                               translated_to_c=False)
        self.gc.stm_operations._gc = self.gc
        self.gc.DEBUG = True
        self.gc.get_size = fake_get_size
        self.gc.trace = fake_trace
        self.gc.weakpointer_offset = fake_weakpointer_offset
        self.gc.root_walker = FakeRootWalker()
        self.gc.setup()

    def teardown_method(self, meth):
        if not hasattr(self, 'gc'):
            return
        for key in self.gc.stm_operations._tls_dict.keys():
            if key != 0:
                self.gc.stm_operations.threadnum = key
                self.gc.teardown_thread()
        self.gc.stm_operations.threadnum = 0

    # ----------
    # test helpers
    def malloc(self, STRUCT, weakref=False, globl='auto'):
        size = llarena.round_up_for_allocation(llmemory.sizeof(STRUCT))
        tid = lltype.cast_primitive(llgroup.HALFWORD, 123 + weakref)
        if globl == 'auto':
            globl = (self.gc.stm_operations.threadnum == 0)
        if globl:
            totalsize = self.gc.gcheaderbuilder.size_gc_header + size
            adr1 = llarena.arena_malloc(llmemory.raw_malloc_usage(totalsize),
                                        1)
            llarena.arena_reserve(adr1, totalsize)
            addr = adr1 + self.gc.gcheaderbuilder.size_gc_header
            self.gc.header(addr).tid = self.gc.combine(tid, GCFLAG_GLOBAL)
            realobj = llmemory.cast_adr_to_ptr(addr, lltype.Ptr(STRUCT))
        else:
            gcref = self.gc.malloc_fixedsize_clear(tid, size,
                                                   contains_weakptr=weakref)
            realobj = lltype.cast_opaque_ptr(lltype.Ptr(STRUCT), gcref)
            addr = llmemory.cast_ptr_to_adr(realobj)
        return realobj, addr
    def select_thread(self, threadnum):
        self.gc.stm_operations.threadnum = threadnum
        if threadnum not in self.gc.stm_operations._tls_dict:
            self.gc.setup_thread()
            self.gc.start_transaction()
    def gcsize(self, S):
        return (llmemory.raw_malloc_usage(llmemory.sizeof(self.gc.HDR)) +
                llmemory.raw_malloc_usage(llmemory.sizeof(S)))
    def checkflags(self, obj, must_have_global, must_have_was_copied,
                              must_have_version='?'):
        if lltype.typeOf(obj) != llmemory.Address:
            obj = llmemory.cast_ptr_to_adr(obj)
        hdr = self.gc.header(obj)
        assert (hdr.tid & GCFLAG_GLOBAL != 0) == must_have_global
        if must_have_was_copied != '?':
            assert (hdr.tid & GCFLAG_WAS_COPIED != 0) == must_have_was_copied
        if must_have_version != '?':
            assert hdr.version == must_have_version
    def read_signed(self, obj, offset):
        meth = getattr(self.gc, 'read_int%d' % WORD)
        return meth(obj, offset)


class TestBasic(StmGCTests):

    def test_gc_creation_works(self):
        pass

    def test_allocate_bump_pointer(self):
        tls = self.gc.get_tls()
        a3 = tls.allocate_bump_pointer(3)
        a4 = tls.allocate_bump_pointer(4)
        a5 = tls.allocate_bump_pointer(5)
        a6 = tls.allocate_bump_pointer(6)
        assert a4 - a3 == 3
        assert a5 - a4 == 4
        assert a6 - a5 == 5

    def test_malloc_fixedsize_clear(self):
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        s = lltype.cast_opaque_ptr(lltype.Ptr(S), gcref)
        assert s.a == 0
        assert s.b == 0
        gcref2 = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        assert gcref2 != gcref

    def test_malloc_main_vs_thread(self):
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        obj = llmemory.cast_ptr_to_adr(gcref)
        assert self.gc.header(obj).tid & GCFLAG_GLOBAL == 0
        #
        self.select_thread(1)
        gcref = self.gc.malloc_fixedsize_clear(123, llmemory.sizeof(S))
        obj = llmemory.cast_ptr_to_adr(gcref)
        assert self.gc.header(obj).tid & GCFLAG_GLOBAL == 0

    def test_write_barrier_exists(self):
        self.select_thread(1)
        t, t_adr = self.malloc(S)
        obj = self.gc.stm_writebarrier(t_adr)     # local object
        assert obj == t_adr
        #
        self.select_thread(0)
        s, s_adr = self.malloc(S)
        #
        self.select_thread(1)
        self.gc.header(s_adr).tid |= GCFLAG_WAS_COPIED
        self.gc.header(t_adr).tid |= GCFLAG_WAS_COPIED | GCFLAG_VISITED
        self.gc.header(t_adr).version = s_adr
        self.gc.stm_operations._tldicts[1][s_adr] = t_adr
        obj = self.gc.stm_writebarrier(s_adr)     # global copied object
        assert obj == t_adr
        assert self.gc.stm_operations._transactional_copies == []

    def test_write_barrier_new(self):
        self.select_thread(0)
        s, s_adr = self.malloc(S)
        s.a = 12
        s.b = 34
        #
        self.select_thread(1)                # global object, not copied so far
        t_adr = self.gc.stm_writebarrier(s_adr)
        assert t_adr != s_adr
        t = t_adr.ptr
        assert t.a == 12
        assert t.b == 34
        assert self.gc.stm_operations._transactional_copies == [(s_adr, t_adr)]
        #
        u_adr = self.gc.stm_writebarrier(s_adr)  # again
        assert u_adr == t_adr
        #
        u_adr = self.gc.stm_writebarrier(u_adr)  # local object
        assert u_adr == t_adr

    def test_write_barrier_main_thread(self):
        t, t_adr = self.malloc(S, globl=False)
        self.checkflags(t_adr, False, False)
        obj = self.gc.stm_writebarrier(t_adr)     # main thread, but not global
        assert obj == t_adr
        self.checkflags(obj, False, False)

    def test_random_gc_usage(self):
        import random
        from pypy.rpython.memory.gc.test import test_stmtls
        self.gc.root_walker = test_stmtls.FakeRootWalker()
        #
        sr2 = {}    # {obj._obj: obj._obj} following the 'sr2' attribute
        sr3 = {}    # {obj._obj: obj._obj} following the 'sr3' attribute
        #
        def reachable(source_objects):
            pending = list(source_objects)
            found = set(obj._obj for obj in pending)
            for x in pending:
                for name in ('sr2', 'sr3'):
                    obj = self.gc.stm_operations.read_attribute(x, name)
                    if obj and obj._obj not in found:
                        found.add(obj._obj)
                        pending.append(obj)
            return found
        #
        def shape_of_reachable(source_object, can_be_indirect=True):
            shape = []
            pending = [source_object]
            found = {source_object._obj: 0}
            for x in pending:
                for name in ('sr2', 'sr3'):
                    obj = self.gc.stm_operations.read_attribute(x, name)
                    if not can_be_indirect:
                        assert obj == getattr(x, name)
                    if not obj:
                        shape.append(None)
                    else:
                        if obj._obj not in found:
                            found[obj._obj] = len(found)
                            pending.append(obj)
                        shape.append(found[obj._obj])
            return shape
        #
        prebuilt = [self.malloc(SR, globl=True)[0] for i in range(15)]
        globals = set(obj._obj for obj in prebuilt)
        root_objects = prebuilt[:]
        all_objects = root_objects[:]
        NO_OBJECT = lltype.nullptr(SR)
        #
        for iteration in range(3):
            # add 6 freshly malloced objects from the nursery
            new_objects = [self.malloc(SR, globl=False)[0] for i in range(6)]
            set_new_objects = set(obj._obj for obj in new_objects)
            all_objects = all_objects + new_objects
            set_all_objects = set(obj._obj for obj in all_objects)
            #
            # pick 4 random objects to be stack roots
            fromstack = random.sample(all_objects, 4)
            root_objects = prebuilt + fromstack
            #
            # randomly add or remove connections between objects, until they
            # are all reachable from root_objects
            for trying in xrange(200):
                missing_objects = set_all_objects - reachable(root_objects)
                if not missing_objects:
                    break
                srcobj = random.choice(all_objects)
                # give a higher chance to 'missing_objects', but also
                # allows other objects
                missing_objects = [obj._as_ptr() for obj in missing_objects]
                missing_objects.append(NO_OBJECT)
                missing_objects *= 2
                missing_objects.extend(all_objects)
                dstobj = random.choice(missing_objects)
                name = random.choice(('sr2', 'sr3'))
                src_adr = llmemory.cast_ptr_to_adr(srcobj)
                adr2 = self.gc.stm_writebarrier(src_adr)
                obj2 = llmemory.cast_adr_to_ptr(adr2, lltype.Ptr(SR))
                setattr(obj2, name, dstobj)
            #
            # Record the shape of the graph of reachable objects
            shapes = [shape_of_reachable(obj) for obj in root_objects]
            #
            # Do a minor collection
            self.gc.root_walker.current_stack = fromstack[:]
            self.gc.collect(0)
            #
            # Reload 'fromstack', which may have moved, and compare the shape
            # of the graph of reachable objects now
            fromstack[:] = self.gc.root_walker.current_stack
            root_objects = prebuilt + fromstack
            shapes2 = [shape_of_reachable(obj, can_be_indirect=False)
                       for obj in root_objects]
            assert shapes == shapes2
            #
            # Reset the list of all objects for the next iteration
            all_objects = [obj._as_ptr() for obj in reachable(root_objects)]
            #
            # Check the GLOBAL flag, and check that the objects really survived
            for obj in all_objects:
                self.checkflags(obj, obj._obj in globals, '?')
                localobj = self.gc.stm_operations.tldict_lookup(
                    llmemory.cast_ptr_to_adr(obj))
                if localobj:
                    self.checkflags(localobj, False, False)
            print 'Iteration %d finished' % iteration

    def test_relocalize_objects_after_transaction_break(self):
        from pypy.rpython.memory.gc.test import test_stmtls
        self.gc.root_walker = test_stmtls.FakeRootWalker()
        #
        tr1, tr1_adr = self.malloc(SR, globl=True)   # three prebuilt objects
        tr2, tr2_adr = self.malloc(SR, globl=True)
        tr3, tr3_adr = self.malloc(SR, globl=True)
        tr1.sr2 = tr2
        self.gc.root_walker.current_stack = [tr1]
        sr1_adr = self.gc.stm_writebarrier(tr1_adr)
        assert sr1_adr != tr1_adr
        sr2_adr = self.gc.stm_writebarrier(tr2_adr)
        assert sr2_adr != tr2_adr
        sr3_adr = self.gc.stm_writebarrier(tr3_adr)
        assert sr3_adr != tr3_adr
        self.checkflags(sr1_adr, False, True)    # sr1 is local
        self.checkflags(sr2_adr, False, True)    # sr2 is local
        self.checkflags(sr3_adr, False, True)    # sr3 is local
        #
        self.gc.stop_transaction()
        self.gc.start_transaction()
        self.checkflags(tr1_adr, True, True)     # tr1 has become global again
        self.checkflags(tr2_adr, True, True)     # tr2 has become global again
        self.checkflags(tr3_adr, True, True)     # tr3 has become global again

    def test_non_prebuilt_relocalize_after_transaction_break(self):
        from pypy.rpython.memory.gc.test import test_stmtls
        self.gc.root_walker = test_stmtls.FakeRootWalker()
        #
        tr1, tr1_adr = self.malloc(SR, globl=False)  # local
        tr2, tr2_adr = self.malloc(SR, globl=False)  # local
        self.checkflags(tr1_adr, False, False)    # check that it is local
        self.checkflags(tr2_adr, False, False)    # check that it is local
        tr1.sr2 = tr2
        self.gc.root_walker.current_stack = [tr1]
        self.gc.stop_transaction()
        # tr1 and tr2 moved out of the nursery: check that
        [sr1] = self.gc.root_walker.current_stack
        assert sr1._obj0 != tr1._obj0
        sr2 = sr1.sr2
        assert sr2 and sr2 != sr1 and not sr2.sr2
        assert sr2._obj0 != tr2._obj0
        sr1_adr = llmemory.cast_ptr_to_adr(sr1)
        sr2_adr = llmemory.cast_ptr_to_adr(sr2)
        self.checkflags(sr1_adr, True, False)     # sr1 is a global
        self.checkflags(sr2_adr, True, False)     # sr2 is a global
        self.gc.start_transaction()
        self.checkflags(sr1_adr, True, False)     # sr1 is still global
        self.checkflags(sr2_adr, True, False)     # sr2 is still global

    def test_collect_from_main_thread_was_global_objects(self):
        tr1, tr1_adr = self.malloc(SR, globl=True)  # a global prebuilt object
        sr2, sr2_adr = self.malloc(SR, globl=False) # sr2 is a local
        self.checkflags(sr2_adr, False, False)      # check that sr2 is a local
        sr1_adr = self.gc.stm_writebarrier(tr1_adr)
        assert sr1_adr != tr1_adr                   # sr1 is the local copy
        sr1 = llmemory.cast_adr_to_ptr(sr1_adr, lltype.Ptr(SR))
        sr1.sr2 = sr2
        self.gc.stop_transaction()
        self.checkflags(tr1_adr, True, True)       # tr1 is still global
        assert tr1.sr2 == lltype.nullptr(SR)   # the copying is left to C code
        tr2 = sr1.sr2                          # from sr1
        assert tr2
        assert tr2._obj0 != sr2._obj0
        tr2_adr = llmemory.cast_ptr_to_adr(tr2)
        self.checkflags(tr2_adr, True, False)      # tr2 is now global

    def test_commit_transaction_empty(self):
        self.select_thread(1)
        s, s_adr = self.malloc(S)
        t, t_adr = self.malloc(S)
        self.gc.stop_transaction()    # no roots
        self.gc.start_transaction()
        main_tls = self.gc.get_tls()
        assert main_tls.nursery_free == main_tls.nursery_start   # empty

    def test_commit_tldict_entry_with_global_references(self):
        t, t_adr = self.malloc(S)
        tr, tr_adr = self.malloc(SR)
        tr.s1 = t
        self.select_thread(1)
        sr_adr = self.gc.stm_writebarrier(tr_adr)
        assert sr_adr != tr_adr
        s_adr = self.gc.stm_writebarrier(t_adr)
        assert s_adr != t_adr

    def test_commit_local_obj_with_global_references(self):
        t, t_adr = self.malloc(S)
        tr, tr_adr = self.malloc(SR)
        tr.s1 = t
        self.select_thread(1)
        sr_adr = self.gc.stm_writebarrier(tr_adr)
        assert sr_adr != tr_adr
        sr = llmemory.cast_adr_to_ptr(sr_adr, lltype.Ptr(SR))
        sr2, sr2_adr = self.malloc(SR)
        sr.sr2 = sr2

    def test_commit_with_ref_to_local_copy(self):
        tr, tr_adr = self.malloc(SR)
        sr_adr = self.gc.stm_writebarrier(tr_adr)
        assert sr_adr != tr_adr
        sr = llmemory.cast_adr_to_ptr(sr_adr, lltype.Ptr(SR))
        sr.sr2 = sr
        self.gc.stop_transaction()
        assert sr.sr2 == tr

    def test_do_get_size(self):
        s1, s1_adr = self.malloc(S)
        assert (repr(self.gc._stm_getsize(s1_adr)) ==
                repr(fake_get_size(s1_adr)))

    def test_id_of_global(self):
        s, s_adr = self.malloc(S)
        i = self.gc.id(s)
        assert i == llmemory.cast_adr_to_int(s_adr)

    def test_id_of_globallocal(self):
        s, s_adr = self.malloc(S)
        t_adr = self.gc.stm_writebarrier(s_adr)   # make a local copy
        assert t_adr != s_adr
        t = llmemory.cast_adr_to_ptr(t_adr, llmemory.GCREF)
        i = self.gc.id(t)
        assert i == llmemory.cast_adr_to_int(s_adr)
        assert i == self.gc.id(s)
        self.gc.stop_transaction()
        assert i == self.gc.id(s)

    def test_id_of_local_nonsurviving(self):
        s, s_adr = self.malloc(S, globl=False)
        i = self.gc.id(s)
        assert i != llmemory.cast_adr_to_int(s_adr)
        assert i == self.gc.id(s)
        self.gc.stop_transaction()

    def test_id_of_local_surviving(self):
        sr1, sr1_adr = self.malloc(SR, globl=True)
        assert sr1.s1 == lltype.nullptr(S)
        assert sr1.sr2 == lltype.nullptr(SR)
        t2, t2_adr = self.malloc(S, globl=False)
        t2.a = 423
        tr1_adr = self.gc.stm_writebarrier(sr1_adr)
        assert tr1_adr != sr1_adr
        tr1 = llmemory.cast_adr_to_ptr(tr1_adr, lltype.Ptr(SR))
        tr1.s1 = t2
        i = self.gc.id(t2)
        assert i not in (llmemory.cast_adr_to_int(sr1_adr),
                         llmemory.cast_adr_to_int(t2_adr),
                         llmemory.cast_adr_to_int(tr1_adr))
        assert i == self.gc.id(t2)
        self.gc.stop_transaction()
        s2 = tr1.s1       # tr1 is a root, so not copied yet
        assert s2 and s2.a == 423 and s2._obj0 != t2._obj0
        assert self.gc.id(s2) == i

    def test_hash_of_global(self):
        s, s_adr = self.malloc(S)
        i = self.gc.identityhash(s)
        assert i == mangle_hash(llmemory.cast_adr_to_int(s_adr))

    def test_hash_of_globallocal(self):
        s, s_adr = self.malloc(S, globl=True)
        t_adr = self.gc.stm_writebarrier(s_adr)   # make a local copy
        t = llmemory.cast_adr_to_ptr(t_adr, llmemory.GCREF)
        i = self.gc.identityhash(t)
        assert i == mangle_hash(llmemory.cast_adr_to_int(s_adr))
        assert i == self.gc.identityhash(s)
        self.gc.stop_transaction()
        assert i == self.gc.identityhash(s)

    def test_hash_of_local_nonsurviving(self):
        s, s_adr = self.malloc(S, globl=False)
        i = self.gc.identityhash(s)
        assert i != mangle_hash(llmemory.cast_adr_to_int(s_adr))
        assert i == self.gc.identityhash(s)
        self.gc.stop_transaction()

    def test_hash_of_local_surviving(self):
        sr1, sr1_adr = self.malloc(SR, globl=True)
        t2, t2_adr = self.malloc(S, globl=False)
        t2.a = 424
        tr1_adr = self.gc.stm_writebarrier(sr1_adr)
        assert tr1_adr != sr1_adr
        tr1 = llmemory.cast_adr_to_ptr(tr1_adr, lltype.Ptr(SR))
        tr1.s1 = t2
        i = self.gc.identityhash(t2)
        assert i not in map(mangle_hash,
                        (llmemory.cast_adr_to_int(sr1_adr),
                         llmemory.cast_adr_to_int(t2_adr),
                         llmemory.cast_adr_to_int(tr1_adr)))
        assert i == self.gc.identityhash(t2)
        self.gc.stop_transaction()
        s2 = tr1.s1       # tr1 is a root, so not copied yet
        assert s2 and s2.a == 424 and s2._obj0 != t2._obj0
        assert self.gc.identityhash(s2) == i

    def test_weakref_to_global(self):
        swr1, swr1_adr = self.malloc(SWR, globl=True)
        s2, s2_adr = self.malloc(S, globl=True)
        wr1, wr1_adr = self.malloc(WR, globl=False, weakref=True)
        wr1.wadr = s2_adr
        twr1_adr = self.gc.stm_writebarrier(swr1_adr)
        twr1 = llmemory.cast_adr_to_ptr(twr1_adr, lltype.Ptr(SWR))
        twr1.wr = wr1
        self.gc.stop_transaction()
        wr2 = twr1.wr      # twr1 is a root, so not copied yet
        assert wr2 and wr2._obj0 != wr1._obj0
        assert wr2.wadr == s2_adr   # survives

    def test_weakref_to_local_dying(self):
        swr1, swr1_adr = self.malloc(SWR, globl=True)
        t2, t2_adr = self.malloc(S, globl=False)
        wr1, wr1_adr = self.malloc(WR, globl=False, weakref=True)
        wr1.wadr = t2_adr
        twr1_adr = self.gc.stm_writebarrier(swr1_adr)
        twr1 = llmemory.cast_adr_to_ptr(twr1_adr, lltype.Ptr(SWR))
        twr1.wr = wr1
        self.gc.stop_transaction()
        wr2 = twr1.wr      # twr1 is a root, so not copied yet
        assert wr2 and wr2._obj0 != wr1._obj0
        assert wr2.wadr == llmemory.NULL   # dies

    def test_weakref_to_local_surviving(self):
        sr1, sr1_adr = self.malloc(SR, globl=True)
        swr1, swr1_adr = self.malloc(SWR, globl=True)
        t2, t2_adr = self.malloc(S, globl=False)
        wr1, wr1_adr = self.malloc(WR, globl=False, weakref=True)
        wr1.wadr = t2_adr
        twr1_adr = self.gc.stm_writebarrier(swr1_adr)
        twr1 = llmemory.cast_adr_to_ptr(twr1_adr, lltype.Ptr(SWR))
        twr1.wr = wr1
        tr1_adr = self.gc.stm_writebarrier(sr1_adr)
        tr1 = llmemory.cast_adr_to_ptr(tr1_adr, lltype.Ptr(SR))
        tr1.s1 = t2
        t2.a = 4242
        self.gc.stop_transaction()
        wr2 = twr1.wr      # twr1 is a root, so not copied yet
        assert wr2 and wr2._obj0 != wr1._obj0
        assert wr2.wadr and wr2.wadr.ptr._obj0 != t2_adr.ptr._obj0   # survives
        s2 = llmemory.cast_adr_to_ptr(wr2.wadr, lltype.Ptr(S))
        assert s2.a == 4242
        assert s2 == tr1.s1   # tr1 is a root, so not copied yet

    def test_weakref_to_local_in_main_thread(self):
        from pypy.rpython.memory.gc.test import test_stmtls
        self.gc.root_walker = test_stmtls.FakeRootWalker()
        #
        sr1, sr1_adr = self.malloc(SR, globl=False)
        wr1, wr1_adr = self.malloc(WR, globl=False, weakref=True)
        wr1.wadr = sr1_adr
        #
        self.gc.root_walker.current_stack = [wr1]
        self.gc.collect(0)
        [wr1] = self.gc.root_walker.current_stack
        assert not wr1.wadr        # weakref to dead object
        #
        self.gc.collect(0)
        assert self.gc.root_walker.current_stack == [wr1]
        assert not wr1.wadr

    def test_normalize_global_null(self):
        a = self.gc.stm_normalize_global(llmemory.NULL)
        assert a == llmemory.NULL

    def test_normalize_global_already_global(self):
        sr1, sr1_adr = self.malloc(SR)
        a = self.gc.stm_normalize_global(sr1_adr)
        assert a == sr1_adr

    def test_normalize_global_purely_local(self):
        self.select_thread(1)
        sr1, sr1_adr = self.malloc(SR)
        a = self.gc.stm_normalize_global(sr1_adr)
        assert a == sr1_adr

    def test_normalize_global_local_copy(self):
        sr1, sr1_adr = self.malloc(SR)
        self.select_thread(1)
        tr1_adr = self.gc.stm_writebarrier(sr1_adr)
        a = self.gc.stm_normalize_global(sr1_adr)
        assert a == sr1_adr
        a = self.gc.stm_normalize_global(tr1_adr)
        assert a == sr1_adr

    def test_prebuilt_nongc(self):
        from pypy.rpython.memory.gc.test import test_stmtls
        self.gc.root_walker = test_stmtls.FakeRootWalker()
        NONGC = lltype.Struct('NONGC', ('s', lltype.Ptr(S)))
        nongc = lltype.malloc(NONGC, immortal=True, flavor='raw')
        self.gc.root_walker.prebuilt_nongc = [(nongc, 's')]
        #
        s, _ = self.malloc(S, globl=False)      # a local object
        nongc.s = s
        self.gc.collect(0)                      # keeps LOCAL
        s = nongc.s                             # reload, it moved
        s_adr = llmemory.cast_ptr_to_adr(s)
        self.checkflags(s_adr, False, False)    # check it survived; local
