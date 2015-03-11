import random, os
import cffi

ffi = cffi.FFI()

ffi.cdef("""
typedef struct {
    uintptr_t key;
    char *data;
    ...;
} skipnode_t;

skipnode_t *skiplist_malloc(uintptr_t datasize);
skipnode_t *skiplist_search(skipnode_t *head, uintptr_t searchkey);
void skiplist_insert(skipnode_t *head, skipnode_t *new);
void skiplist_remove(skipnode_t *head, uintptr_t exact_key);
""")

filename = os.path.join(os.path.dirname(__file__), '..', 'src', 'skiplist.c')
lib = ffi.verify(open(filename).read())


def test_insert_search_remove():
    my_head = ffi.new("skipnode_t *")
    assert lib.skiplist_search(my_head, 0) == my_head
    #
    keys = random.sample(xrange(2, 10**9), 50000)
    nodes = {}
    for key in keys:
        node = lib.skiplist_malloc(4)
        node.key = key
        ffi.cast("int *", node.data)[0] = key
        lib.skiplist_insert(my_head, node)
        nodes[key] = node
    #
    random.shuffle(keys)
    for key in keys:
        node = lib.skiplist_search(my_head, key)
        assert nodes[key] == node
        if key + 1 not in nodes:
            assert node == lib.skiplist_search(my_head, key + 1)
    #
    keys.sort()
    following = {}
    preceeding = {}
    for key, next_key in zip(keys[:-1], keys[1:]):
        following[key] = next_key
        preceeding[next_key] = key
    following[0] = keys[0]
    following[keys[-1]] = 10**9
    preceeding[keys[0]] = 0
    #
    for i in range(100000):
        random_key = random.randrange(2, 10**9)
        node = lib.skiplist_search(my_head, random_key)
        assert node.key <= random_key
        if node == my_head:
            assert random_key < following[0]
        else:
            assert node == nodes[node.key]
            assert following[node.key] > random_key
    #
    random_keys = list(keys)
    random.shuffle(random_keys)
    for i in range(10000):
        node = nodes.pop(random_keys.pop())
        prev = preceeding[node.key]
        next = following[node.key]
        following[prev] = next
        preceeding[next] = prev
        lib.skiplist_remove(my_head, node.key)
        if prev == 0:
            assert lib.skiplist_search(my_head, node.key) == my_head
        else:
            assert lib.skiplist_search(my_head, node.key) == nodes[prev]
    #
    for i in range(100000):
        random_key = random.randrange(2, 10**9)
        node = lib.skiplist_search(my_head, random_key)
        assert node.key <= random_key
        if node == my_head:
            assert random_key < following[0]
        else:
            assert node == nodes[node.key]
            assert following[node.key] > random_key
