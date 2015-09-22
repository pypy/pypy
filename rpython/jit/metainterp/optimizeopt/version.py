
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.optimizeopt.optimizer import BasicLoopInfo
from rpython.jit.metainterp.compile import (send_bridge_to_backend, record_loop_or_bridge,
        ResumeGuardDescr, create_empty_loop)


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

    def snapshot(self, loop):
        newloop = loop.clone()
        version = LoopVersion(newloop)
        version.setup_once(self)
        self.versions.append(version)
        # register the faildescr for later stitching
        return version

    def post_loop_compilation(self, loop, jitdriver_sd, metainterp, jitcell_token):
        """ if a loop version is created for a guard instruction (e.g. they are known
            to fail frequently) then a version can be created that is immediatly compiled
            and stitched to the guard.
        """
        metainterp_sd = metainterp.staticdata
        cpu = metainterp_sd.cpu
        if not self.versions:
            return
        # compile each version once for the first fail descr!
        # this assumes that the root trace (= loop) is already compiled
        compiled = {}
        for descr in self.descrs:
            version = self.get(descr)
            if not version:
                # the guard might have been removed from the trace
                continue
            if version not in compiled:
                assert isinstance(descr, ResumeGuardDescr)
                vl = version.create_backend_loop(metainterp, jitcell_token)
                asminfo = send_bridge_to_backend(jitdriver_sd, metainterp_sd,
                                                 descr, vl.inputargs,
                                                 vl.operations, jitcell_token,
                                                 metainterp.box_names_memo)
                record_loop_or_bridge(metainterp_sd, vl)
                assert asminfo is not None
                compiled[version] = (asminfo, descr, version, jitcell_token)
            else:
                param = compiled[version]
                cpu.stitch_bridge(descr, param)

        self.versions = None # dismiss versions


class LoopVersion(object):
    """ A special version of a trace loop. Use loop.snaphost() to
        create one instance and attach it to a guard descr.
        If not attached to a descriptor, it will not be compiled.
    """
    _attrs_ = ('label', 'operations', 'inputargs', 'renamed_inputargs')

    def __init__(self, loop):
        self.loop = loop
        self.inputargs = loop.label.getarglist()
        self.renamed_inputargs = loop.label.getarglist()

    def setup_once(self, info):
        for op in self.loop.operations:
            if not op.is_guard():
                continue
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

    def create_backend_loop(self, metainterp, jitcell_token):
        vl = create_empty_loop(metainterp)
        vl.operations = self.loop.finaloplist(jitcell_token,True)
        vl.inputargs = self.loop.label.getarglist_copy()
        vl.original_jitcell_token = jitcell_token
        return vl


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


