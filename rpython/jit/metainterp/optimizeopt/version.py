
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.optimizeopt.optimizer import BasicLoopInfo

class LoopVersionInfo(BasicLoopInfo):
    def __init__(self, info):
        self.target_token = info.target_token
        self.label_op = info.label_op
        self.extra_same_as = info.extra_same_as
        self.quasi_immutable_deps = info.quasi_immutable_deps
        self.descrs = []
        self.leads_to = {}
        self.insert_index = -1
        self.versions = []

    def mark(self):
        self.insert_index = len(self.descrs)

    def clear(self):
        self.insert_index = -1

    def track(self, op, descr, version):
        assert descr.loop_version()
        i = self.insert_index
        if i >= 0:
            assert i >= 0
            self.descrs.insert(i, descr)
        else:
            self.descrs.append(descr)
        self.leads_to[descr] = version
        assert version.renamed_inputargs is not None

    def remove(self, descr):
        if descr in self.leads_to:
            del self.leads_to[descr]
        else:
            assert 0, "could not remove %s" % descr

    def get(self, descr):
        return self.leads_to.get(descr, None)

    def snapshot(self, operations, label):
        oplist = []
        ignore = (rop.DEBUG_MERGE_POINT,)
        for op in operations:
            if op.getopnum() in ignore:
                continue
            cloned = op.copy_and_change(op.getopnum())
            oplist.append(cloned)
        version = LoopVersion(oplist, label)
        version.setup_once(self)
        self.versions.append(version)
        # register the faildescr for later stitching
        return version

class LoopVersion(object):
    """ A special version of a trace loop. Use loop.snaphost() to
        create one instance and attach it to a guard descr.
        If not attached to a descriptor, it will not be compiled.
    """
    _attrs_ = ('label', 'operations', 'inputargs', 'renamed_inputargs')

    def __init__(self, operations, label):
        self.label = label
        self.operations = operations
        self.inputargs = label.getarglist()
        self.renamed_inputargs = label.getarglist()

    def setup_once(self, info):
        for op in self.operations:
            if op.is_guard():
                olddescr = op.getdescr()
                if not olddescr:
                    continue
                descr = olddescr.clone()
                op.setdescr(descr)
                if descr.loop_version():
                    toversion = info.leads_to.get(olddescr,None)
                    if toversion:
                        info.track(op, descr, toversion)
                    else:
                        assert 0, "olddescr must be found"

    def update_token(self, jitcell_token, all_target_tokens):
        # this is only invoked for versioned loops!
        # TODO
        label_index = index_of_first(rop.LABEL, self.operations, 0)
        label = self.operations[label_index]
        jump = self.operations[-1]
        #
        assert jump.getopnum() == rop.JUMP
        #
        token = TargetToken(jitcell_token)
        token.original_jitcell_token = jitcell_token
        all_target_tokens.append(token)
        if label.getdescr() is None or label.getdescr() is not jump.getdescr():
            label_index = index_of_first(rop.LABEL, self.operations, 1)
            if label_index > 0:
                second_label = self.operations[label_index]
                # set the inner loop
                second_label.setdescr(token)
                jump.setdescr(token)
                # set the first label
                token = TargetToken(jitcell_token)
                token.original_jitcell_token = jitcell_token
                all_target_tokens.append(token)
                label.setdescr(token)
                return
        label.setdescr(token)
        jump.setdescr(token)


#def index_of_first(opnum, operations, pass_by=0):
#    """ returns the position of the first operation matching the opnum.
#    Or -1 if non is found
#    """
#    for i,op in enumerate(operations):
#        if op.getopnum() == opnum:
#            if pass_by == 0:
#                return i
#            else:
#                pass_by -= 1
#    return -1
#
#def find_first_index(self, opnum, pass_by=0):
#    """ return the first index of the operation having the same opnum or -1 """
#    return index_of_first(opnum, self.operations, pass_by)
#
#def find_first(self, opnum, pass_by=0):
#    index = self.find_first_index(opnum, pass_by)
#    if index != -1:
#        return self.operations[index]
#    return None


