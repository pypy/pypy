from pypy.jit.metainterp.history import Const
from pypy.jit.metainterp.resume import Snapshot

class Inliner(object):
    def __init__(self, inputargs, jump_args):
        assert len(inputargs) == len(jump_args)
        self.argmap = {}
        for i in range(len(inputargs)):
            if inputargs[i] in self.argmap:
                assert self.argmap[inputargs[i]] == jump_args[i]
            else:
                self.argmap[inputargs[i]] = jump_args[i]
        self.snapshot_map = {None: None}

    def inline_op(self, newop, ignore_result=False, clone=True,
                  ignore_failargs=False):
        if clone:
            newop = newop.clone()
        args = newop.getarglist()
        newop.initarglist([self.inline_arg(a) for a in args])

        if newop.is_guard():
            args = newop.getfailargs()
            if args and not ignore_failargs:
                newop.setfailargs([self.inline_arg(a) for a in args])
            else:
                newop.setfailargs([])

        if newop.result and not ignore_result:
            old_result = newop.result
            newop.result = newop.result.clonebox()
            self.argmap[old_result] = newop.result

        self.inline_descr_inplace(newop.getdescr())

        return newop

    def inline_descr_inplace(self, descr):
        from pypy.jit.metainterp.compile import ResumeGuardDescr
        if isinstance(descr, ResumeGuardDescr):
            descr.rd_snapshot = self.inline_snapshot(descr.rd_snapshot)

    def inline_arg(self, arg):
        if arg is None:
            return None
        if isinstance(arg, Const):
            return arg
        return self.argmap[arg]

    def inline_snapshot(self, snapshot):
        if snapshot in self.snapshot_map:
            return self.snapshot_map[snapshot]
        boxes = [self.inline_arg(a) for a in snapshot.boxes]
        new_snapshot = Snapshot(self.inline_snapshot(snapshot.prev), boxes)
        self.snapshot_map[snapshot] = new_snapshot
        return new_snapshot

