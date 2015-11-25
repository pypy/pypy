from rpython.rlib import rstm
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.translator.c.node import ContainerNodeFactory, StructNode


def compute_annotation(bookkeeper, hashtable):
    if not hasattr(hashtable, '_obj'):
        h = lltype.malloc(rstm._HASHTABLE_OBJ, zero=True)
        hashtable._obj = h._obj
        translator = bookkeeper.annotator.translator
        try:
            prebuilt_hashtables = translator._prebuilt_hashtables
        except AttributeError:
            prebuilt_hashtables = translator._prebuilt_hashtables = {}
        prebuilt_hashtables[h._obj] = hashtable
        #
        for entry in hashtable._content.values():
            if entry._obj:
                bookkeeper.immutablevalue(entry._obj)
        #
        # When we have a prebuilt hashtable but no calls to create_hashtable()
        # in the final RPython program, the translation state is incomplete.
        # Fix it by emulating a call to create_hashtable().
        s_create_hashtable = bookkeeper.immutablevalue(rstm.create_hashtable)
        bookkeeper.emulate_pbc_call("create_hashtable", s_create_hashtable, [])
        #
    return lltype_to_annotation(lltype.Ptr(rstm._HASHTABLE_OBJ))


def gen_prebuilt_hashtables(f, database):
    nodes = [node for node in database.globalcontainers()
                  if isinstance(node, StmHashtableNode)]
    print >> f
    print >> f, '#define STM_PREBUILT_HASHTABLES  %d' % len(nodes)
    if len(nodes) == 0:
        return
    type_id = database.gctransformer.get_type_id(rstm._STM_HASHTABLE_ENTRY)
    expr_type_id = database.get(type_id)
    print >> f, '#define STM_HASHTABLE_ENTRY_TYPEID  %s' % (expr_type_id,)
    print >> f
    print >> f, 'struct _hashtable_descr_s {'
    print >> f, '\tUnsigned key;'
    print >> f, '\tint globalnum;'
    print >> f, '} __attribute__((packed));'
    print >> f, 'static struct _hashtable_descr_s hashtable_descs[] = {'
    for node in nodes:
        assert node.globalgcnum >= 0
        items = node.get_hashtable_content()
        items.sort(key=lambda entry: entry.index)
        print >> f, '\t{ %d, %d },' % (len(items), node.globalgcnum)
        for entry in items:
            itemcontainer = entry.object._obj.container
            itemnode = database.getcontainernode(itemcontainer)
            assert itemnode.globalgcnum >= 0
            print >> f, '\t\t{ %dL, %d },' % (entry.index, itemnode.globalgcnum)
    print >> f, '};'


class StmHashtableNode(StructNode):
    nodekind = 'stmhashtable'

    def __init__(self, db, T, obj):
        StructNode.__init__(self, db, T, obj)
        # hack to force this type to exist
        T = rstm._STM_HASHTABLE_ENTRY
        container = lltype.malloc(T, zero=True)._as_obj()
        db.gctransformer.consider_constant(T, container)

    def get_hashtable_content(self):
        h = self.db.translator._prebuilt_hashtables[self.obj]
        return h._live_items()

    def basename(self):
        return 'stmhashtable'

    def enum_dependencies(self):
        for entry in self.get_hashtable_content():
            yield entry.object

ContainerNodeFactory[rstm.GcStmHashtable] = StmHashtableNode
