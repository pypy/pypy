from pypy.tool.tls import tlsobject

TLS = tlsobject()

class HintBookkeeper(object):

    def __init__(self, hannotator):
        self.pending_specializations = []
        self.origins = {}
        self.virtual_containers = {}
        self.annotator = hannotator

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        TLS.bookkeeper = self

    def leave(self):
        """End of an operation."""
        del TLS.bookkeeper
        del self.position_key

    def myorigin(self):
        try:
            origin = self.origins[self.position_key]
        except KeyError:
            from pypy.jit import hintmodel
            origin = hintmodel.OriginTreeNode()
            self.origins[self.position_key] = origin
        return origin

    def compute_at_fixpoint(self):
        pass

    def immutableconstant(self, const):
        from pypy.jit import hintmodel
        res = hintmodel.SomeLLAbstractConstant(const.concretetype, {})
        res.const = const.value
        return res

    def current_op_concretetype(self):
        _, block, i = self.position_key
        op = block.operations[i]
        return op.result.concretetype

    def getvirtualcontainerdef(self, TYPE, constructor=None):
        try:
            res = self.virtual_containers[self.position_key]
            assert res.T == TYPE
        except KeyError:
            if constructor is None:
                from pypy.jit.hintcontainer import virtualcontainerdef
                constructor = virtualcontainerdef
            res = constructor(self, TYPE)
            self.virtual_containers[self.position_key] = res
        return res

    def warning(self, msg):
        return self.annotator.warning(msg)

# get current bookkeeper

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    try:
        return TLS.bookkeeper
    except AttributeError:
        return None
