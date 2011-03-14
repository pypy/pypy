import sys
from pypy.tool.pairtype import extendabletype
from pypy.jit.backend.x86.regloc import ImmedLoc, StackLoc


class JumpRemapper(object):

    def move(self, src, dst):
        """Called to generate a move from src to dst."""
        raise NotImplementedError

    def push(self, src):
        """Called to temporarily save away the value of src."""
        raise NotImplementedError

    def pop(self, dst):
        """Called after push() to restore the saved value into dst."""
        raise NotImplementedError

    def remap_frame_layout(self, src_locations, dst_locations):
        pending_dests = len(dst_locations)
        srccount = {}    # maps dst_locations to how many times the same
                         # location appears in src_locations
        for dst in dst_locations:
            key = dst._getregkey()
            assert key not in srccount, "duplicate value in dst_locations!"
            srccount[key] = 0
        for i in range(len(dst_locations)):
            src = src_locations[i]
            if isinstance(src, ImmedLoc):
                continue
            key = src._getregkey()
            if key in srccount:
                if key == dst_locations[i]._getregkey():
                    srccount[key] = -sys.maxint     # ignore a move "x = x"
                    pending_dests -= 1
                else:
                    srccount[key] += 1

        while pending_dests > 0:
            progress = False
            for i in range(len(dst_locations)):
                dst = dst_locations[i]
                key = dst._getregkey()
                if srccount[key] == 0:
                    srccount[key] = -1       # means "it's done"
                    pending_dests -= 1
                    src = src_locations[i]
                    if not isinstance(src, ImmedLoc):
                        key = src._getregkey()
                        if key in srccount:
                            srccount[key] -= 1
                    self.move(src, dst)
                    progress = True
            if not progress:
                # we are left with only pure disjoint cycles
                sources = {}     # maps dst_locations to src_locations
                for i in range(len(dst_locations)):
                    src = src_locations[i]
                    dst = dst_locations[i]
                    sources[dst._getregkey()] = src
                #
                for i in range(len(dst_locations)):
                    dst = dst_locations[i]
                    originalkey = dst._getregkey()
                    if srccount[originalkey] >= 0:
                        self.push(dst)
                        while True:
                            key = dst._getregkey()
                            assert srccount[key] == 1
                            # ^^^ because we are in a simple cycle
                            srccount[key] = -1
                            pending_dests -= 1
                            src = sources[key]
                            if src._getregkey() == originalkey:
                                break
                            self.move(src, dst)
                            dst = src
                        self.pop(dst)
                assert pending_dests == 0


class ConcreteJumpRemapper(JumpRemapper):

    def get_tmp_reg(self, src):
        """Get a temporary register suitable for copying src."""
        raise NotImplementedError

    def move(self, src, dst):
        if dst.is_memory_reference() and src.is_memory_reference():
            tmpreg = self.get_tmp_reg(src)
            self.simple_move(src, tmpreg)
            src = tmpreg
        self.simple_move(src, dst)

    def simple_move(self, src, dst):
        raise NotImplementedError
