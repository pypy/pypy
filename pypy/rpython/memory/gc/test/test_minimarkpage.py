import py
from pypy.rpython.memory.gc.minimarkpage import ArenaCollection
from pypy.rpython.memory.gc.minimarkpage import PAGE_HEADER, PAGE_PTR
from pypy.rpython.memory.gc.minimarkpage import PAGE_NULL, WORD
from pypy.rpython.memory.gc.minimarkpage import _dummy_size
from pypy.rpython.lltypesystem import lltype, llmemory, llarena
from pypy.rpython.lltypesystem.llmemory import cast_ptr_to_adr

NULL = llmemory.NULL
SHIFT = WORD
hdrsize = llmemory.raw_malloc_usage(llmemory.sizeof(PAGE_HEADER))


def test_allocate_arena():
    ac = ArenaCollection(SHIFT + 16*20, 16, 1)
    ac.allocate_new_arena()
    assert ac.num_uninitialized_pages == 20
    ac.uninitialized_pages + 16*20   # does not raise
    py.test.raises(llarena.ArenaError, "ac.uninitialized_pages + 16*20 + 1")
    #
    ac = ArenaCollection(SHIFT + 16*20 + 7, 16, 1)
    ac.allocate_new_arena()
    assert ac.num_uninitialized_pages == 20
    ac.uninitialized_pages + 16*20 + 7   # does not raise
    py.test.raises(llarena.ArenaError, "ac.uninitialized_pages + 16*20 + 16")


def test_allocate_new_page():
    pagesize = hdrsize + 16
    arenasize = pagesize * 4 - 1
    #
    def checknewpage(page, size_class):
        size = WORD * size_class
        assert page.nuninitialized == (pagesize - hdrsize) // size
        assert page.nfree == 0
        page1 = page.freeblock - hdrsize
        assert llmemory.cast_ptr_to_adr(page) == page1
        assert page.nextpage == PAGE_NULL
    #
    ac = ArenaCollection(arenasize, pagesize, 99)
    assert ac.num_uninitialized_pages == 0
    assert ac.total_memory_used == 0
    #
    page = ac.allocate_new_page(5)
    checknewpage(page, 5)
    assert ac.num_uninitialized_pages == 2
    assert ac.uninitialized_pages - pagesize == cast_ptr_to_adr(page)
    assert ac.page_for_size[5] == page
    #
    page = ac.allocate_new_page(3)
    checknewpage(page, 3)
    assert ac.num_uninitialized_pages == 1
    assert ac.uninitialized_pages - pagesize == cast_ptr_to_adr(page)
    assert ac.page_for_size[3] == page
    #
    page = ac.allocate_new_page(4)
    checknewpage(page, 4)
    assert ac.num_uninitialized_pages == 0
    assert ac.page_for_size[4] == page


def arena_collection_for_test(pagesize, pagelayout, fill_with_objects=False):
    assert " " not in pagelayout.rstrip(" ")
    nb_pages = len(pagelayout)
    arenasize = pagesize * (nb_pages + 1) - 1
    ac = ArenaCollection(arenasize, pagesize, 9*WORD)
    #
    def link(pageaddr, size_class, size_block, nblocks, nusedblocks, step=1):
        assert step in (1, 2)
        llarena.arena_reserve(pageaddr, llmemory.sizeof(PAGE_HEADER))
        page = llmemory.cast_adr_to_ptr(pageaddr, PAGE_PTR)
        if step == 1:
            page.nfree = 0
            page.nuninitialized = nblocks - nusedblocks
        else:
            page.nfree = nusedblocks
            page.nuninitialized = nblocks - 2*nusedblocks
        if nusedblocks < nblocks:
            page.freeblock = pageaddr + hdrsize + nusedblocks * size_block
            chainedlists = ac.page_for_size
        else:
            page.freeblock = NULL
            chainedlists = ac.full_page_for_size
        page.nextpage = chainedlists[size_class]
        chainedlists[size_class] = page
        if fill_with_objects:
            for i in range(0, nusedblocks*step, step):
                objaddr = pageaddr + hdrsize + i * size_block
                llarena.arena_reserve(objaddr, _dummy_size(size_block))
            if step == 2:
                prev = 'page.freeblock'
                for i in range(1, nusedblocks*step, step):
                    holeaddr = pageaddr + hdrsize + i * size_block
                    llarena.arena_reserve(holeaddr,
                                          llmemory.sizeof(llmemory.Address))
                    exec '%s = holeaddr' % prev in globals(), locals()
                    prevhole = holeaddr
                    prev = 'prevhole.address[0]'
                endaddr = pageaddr + hdrsize + 2*nusedblocks * size_block
                exec '%s = endaddr' % prev in globals(), locals()
    #
    ac.allocate_new_arena()
    num_initialized_pages = len(pagelayout.rstrip(" "))
    ac._startpageaddr = ac.uninitialized_pages
    ac.uninitialized_pages += pagesize * num_initialized_pages
    ac.num_uninitialized_pages -= num_initialized_pages
    #
    for i in reversed(range(num_initialized_pages)):
        pageaddr = pagenum(ac, i)
        c = pagelayout[i]
        if '1' <= c <= '9':   # a partially used page (1 block free)
            size_class = int(c)
            size_block = WORD * size_class
            nblocks = (pagesize - hdrsize) // size_block
            link(pageaddr, size_class, size_block, nblocks, nblocks-1)
        elif c == '.':    # a free, but initialized, page
            llarena.arena_reserve(pageaddr, llmemory.sizeof(llmemory.Address))
            pageaddr.address[0] = ac.free_pages
            ac.free_pages = pageaddr
        elif c == '#':    # a random full page, in the list 'full_pages'
            size_class = fill_with_objects or 1
            size_block = WORD * size_class
            nblocks = (pagesize - hdrsize) // size_block
            link(pageaddr, size_class, size_block, nblocks, nblocks)
        elif c == '/':    # a page 1/3 allocated, 1/3 freed, 1/3 uninit objs
            size_class = fill_with_objects or 1
            size_block = WORD * size_class
            nblocks = (pagesize - hdrsize) // size_block
            link(pageaddr, size_class, size_block, nblocks, nblocks // 3,
                 step=2)
    #
    ac.allocate_new_arena = lambda: should_not_allocate_new_arenas
    return ac


def pagenum(ac, i):
    return ac._startpageaddr + ac.page_size * i

def getpage(ac, i):
    return llmemory.cast_adr_to_ptr(pagenum(ac, i), PAGE_PTR)

def checkpage(ac, page, expected_position):
    assert llmemory.cast_ptr_to_adr(page) == pagenum(ac, expected_position)


def test_simple_arena_collection():
    pagesize = hdrsize + 16
    ac = arena_collection_for_test(pagesize, "##....#   ")
    #
    assert ac.free_pages == pagenum(ac, 2)
    page = ac.allocate_new_page(1); checkpage(ac, page, 2)
    assert ac.free_pages == pagenum(ac, 3)
    page = ac.allocate_new_page(2); checkpage(ac, page, 3)
    assert ac.free_pages == pagenum(ac, 4)
    page = ac.allocate_new_page(3); checkpage(ac, page, 4)
    assert ac.free_pages == pagenum(ac, 5)
    page = ac.allocate_new_page(4); checkpage(ac, page, 5)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 3
    page = ac.allocate_new_page(5); checkpage(ac, page, 7)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 2
    page = ac.allocate_new_page(6); checkpage(ac, page, 8)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 1
    page = ac.allocate_new_page(7); checkpage(ac, page, 9)
    assert ac.free_pages == NULL and ac.num_uninitialized_pages == 0


def chkob(ac, num_page, pos_obj, obj):
    pageaddr = pagenum(ac, num_page)
    assert obj == pageaddr + hdrsize + pos_obj


def test_malloc_common_case():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    assert ac.total_memory_used == 0   # so far
    obj = ac.malloc(2*WORD); chkob(ac, 1, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 5, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 3, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 4*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 0*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 6, 4*WORD, obj)
    assert ac.total_memory_used == 11*2*WORD

def test_malloc_mixed_sizes():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#23..2 ")
    obj = ac.malloc(2*WORD); chkob(ac, 1, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 2, 3*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 5, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 3, 0*WORD, obj)  # 3rd page -> size 3
    obj = ac.malloc(2*WORD); chkob(ac, 4, 0*WORD, obj)  # 4th page -> size 2
    obj = ac.malloc(3*WORD); chkob(ac, 3, 3*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 4, 2*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 6, 0*WORD, obj)  # 6th page -> size 3
    obj = ac.malloc(2*WORD); chkob(ac, 4, 4*WORD, obj)
    obj = ac.malloc(3*WORD); chkob(ac, 6, 3*WORD, obj)

def test_malloc_from_partial_page():
    pagesize = hdrsize + 18*WORD
    ac = arena_collection_for_test(pagesize, "/.", fill_with_objects=2)
    page = getpage(ac, 0)
    assert page.nfree == 3
    assert page.nuninitialized == 3
    chkob(ac, 0, 2*WORD, page.freeblock)
    #
    obj = ac.malloc(2*WORD); chkob(ac, 0,  2*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 0,  6*WORD, obj)
    assert page.nfree == 1
    assert page.nuninitialized == 3
    chkob(ac, 0, 10*WORD, page.freeblock)
    #
    obj = ac.malloc(2*WORD); chkob(ac, 0, 10*WORD, obj)
    assert page.nfree == 0
    assert page.nuninitialized == 3
    chkob(ac, 0, 12*WORD, page.freeblock)
    #
    obj = ac.malloc(2*WORD); chkob(ac, 0, 12*WORD, obj)
    assert page.nuninitialized == 2
    obj = ac.malloc(2*WORD); chkob(ac, 0, 14*WORD, obj)
    obj = ac.malloc(2*WORD); chkob(ac, 0, 16*WORD, obj)
    assert page.nfree == 0
    assert page.nuninitialized == 0
    obj = ac.malloc(2*WORD); chkob(ac, 1,  0*WORD, obj)


def test_malloc_new_arena():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "### ")
    obj = ac.malloc(2*WORD); chkob(ac, 3, 0*WORD, obj)  # 3rd page -> size 2
    #
    del ac.allocate_new_arena    # restore the one from the class
    arena_size = ac.arena_size
    obj = ac.malloc(3*WORD)                             # need a new arena
    assert ac.num_uninitialized_pages == (arena_size // ac.page_size
                                          - 1    # for start_of_page()
                                          - 1    # the just-allocated page
                                          )

class OkToFree(object):
    def __init__(self, ac, answer):
        assert callable(answer) or 0.0 <= answer <= 1.0
        self.ac = ac
        self.answer = answer
        self.lastnum = 0.0
        self.seen = {}

    def __call__(self, addr):
        if callable(self.answer):
            ok_to_free = self.answer(addr)
        else:
            self.lastnum += self.answer
            ok_to_free = self.lastnum >= 1.0
            if ok_to_free:
                self.lastnum -= 1.0
        key = addr - self.ac._startpageaddr
        assert key not in self.seen
        self.seen[key] = ok_to_free
        return ok_to_free

def test_mass_free_partial_remains():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "2", fill_with_objects=2)
    ok_to_free = OkToFree(ac, False)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize + 0*WORD: False,
                               hdrsize + 2*WORD: False}
    page = getpage(ac, 0)
    assert page == ac.page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 1
    assert page.nfree == 0
    chkob(ac, 0, 4*WORD, page.freeblock)
    assert ac.free_pages == NULL

def test_mass_free_emptied_page():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "2", fill_with_objects=2)
    ok_to_free = OkToFree(ac, True)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize + 0*WORD: True,
                               hdrsize + 2*WORD: True}
    pageaddr = pagenum(ac, 0)
    assert pageaddr == ac.free_pages
    assert pageaddr.address[0] == NULL
    assert ac.page_for_size[2] == PAGE_NULL

def test_mass_free_full_remains_full():
    pagesize = hdrsize + 7*WORD
    ac = arena_collection_for_test(pagesize, "#", fill_with_objects=2)
    ok_to_free = OkToFree(ac, False)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize + 0*WORD: False,
                               hdrsize + 2*WORD: False,
                               hdrsize + 4*WORD: False}
    page = getpage(ac, 0)
    assert page == ac.full_page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 0
    assert page.nfree == 0
    assert page.freeblock == NULL
    assert ac.free_pages == NULL
    assert ac.page_for_size[2] == PAGE_NULL

def test_mass_free_full_is_partially_emptied():
    pagesize = hdrsize + 9*WORD
    ac = arena_collection_for_test(pagesize, "#", fill_with_objects=2)
    ok_to_free = OkToFree(ac, 0.5)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize + 0*WORD: False,
                               hdrsize + 2*WORD: True,
                               hdrsize + 4*WORD: False,
                               hdrsize + 6*WORD: True}
    page = getpage(ac, 0)
    pageaddr = pagenum(ac, 0)
    assert page == ac.page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 0
    assert page.nfree == 2
    assert page.freeblock == pageaddr + hdrsize + 2*WORD
    assert page.freeblock.address[0] == pageaddr + hdrsize + 6*WORD
    assert page.freeblock.address[0].address[0] == NULL
    assert ac.free_pages == NULL
    assert ac.full_page_for_size[2] == PAGE_NULL

def test_mass_free_half_page_remains():
    pagesize = hdrsize + 24*WORD
    ac = arena_collection_for_test(pagesize, "/", fill_with_objects=2)
    page = getpage(ac, 0)
    assert page.nuninitialized == 4
    assert page.nfree == 4
    #
    ok_to_free = OkToFree(ac, False)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize +  0*WORD: False,
                               hdrsize +  4*WORD: False,
                               hdrsize +  8*WORD: False,
                               hdrsize + 12*WORD: False}
    page = getpage(ac, 0)
    pageaddr = pagenum(ac, 0)
    assert page == ac.page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 4
    assert page.nfree == 4
    assert page.freeblock == pageaddr + hdrsize + 2*WORD
    assert page.freeblock.address[0] == pageaddr + hdrsize + 6*WORD
    assert page.freeblock.address[0].address[0] == \
                                        pageaddr + hdrsize + 10*WORD
    assert page.freeblock.address[0].address[0].address[0] == \
                                        pageaddr + hdrsize + 14*WORD
    assert ac.free_pages == NULL
    assert ac.full_page_for_size[2] == PAGE_NULL

def test_mass_free_half_page_becomes_more_free():
    pagesize = hdrsize + 24*WORD
    ac = arena_collection_for_test(pagesize, "/", fill_with_objects=2)
    page = getpage(ac, 0)
    assert page.nuninitialized == 4
    assert page.nfree == 4
    #
    ok_to_free = OkToFree(ac, 0.5)
    ac.mass_free(ok_to_free)
    assert ok_to_free.seen == {hdrsize +  0*WORD: False,
                               hdrsize +  4*WORD: True,
                               hdrsize +  8*WORD: False,
                               hdrsize + 12*WORD: True}
    page = getpage(ac, 0)
    pageaddr = pagenum(ac, 0)
    assert page == ac.page_for_size[2]
    assert page.nextpage == PAGE_NULL
    assert page.nuninitialized == 4
    assert page.nfree == 6
    fb = page.freeblock
    assert fb == pageaddr + hdrsize + 2*WORD
    assert fb.address[0] == pageaddr + hdrsize + 4*WORD
    assert fb.address[0].address[0] == pageaddr + hdrsize + 6*WORD
    assert fb.address[0].address[0].address[0] == \
                                       pageaddr + hdrsize + 10*WORD
    assert fb.address[0].address[0].address[0].address[0] == \
                                       pageaddr + hdrsize + 12*WORD
    assert fb.address[0].address[0].address[0].address[0].address[0] == \
                                       pageaddr + hdrsize + 14*WORD
    assert ac.free_pages == NULL
    assert ac.full_page_for_size[2] == PAGE_NULL

# ____________________________________________________________

def test_random():
    import random
    pagesize = hdrsize + 24*WORD
    num_pages = 28
    ac = arena_collection_for_test(pagesize, " " * num_pages)
    live_objects = {}
    #
    # Run the test until ac.allocate_new_arena() is called.
    class DoneTesting(Exception):
        pass
    def done_testing():
        raise DoneTesting
    ac.allocate_new_arena = done_testing
    #
    try:
        while True:
            #
            # Allocate some more objects
            for i in range(random.randrange(50, 100)):
                size_class = random.randrange(1, 7)
                obj = ac.malloc(size_class * WORD)
                at = obj - ac._startpageaddr
                assert at not in live_objects
                live_objects[at] = size_class * WORD
            #
            # Free half the objects, randomly
            ok_to_free = OkToFree(ac, lambda obj: random.random() < 0.5)
            ac.mass_free(ok_to_free)
            #
            # Check that we have seen all objects
            assert sorted(ok_to_free.seen) == sorted(live_objects)
            surviving_total_size = 0
            for at, freed in ok_to_free.seen.items():
                if freed:
                    del live_objects[at]
                else:
                    surviving_total_size += live_objects[at]
            assert ac.total_memory_used == surviving_total_size
    except DoneTesting:
        # the following output looks cool on a 112-character-wide terminal.
        print ac._startpageaddr.arena.usagemap
