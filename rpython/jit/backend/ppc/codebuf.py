from pypy.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin

class MachineCodeBlockWrapper(BlockBuilderMixin):
    def __init__(self):
        self.init_block_builder()
