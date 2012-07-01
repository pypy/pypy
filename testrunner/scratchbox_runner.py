
""" This is a very hackish runner for cross compilation toolchain scratchbox.
Later on we might come out with some general solution
"""

import os

import runner

class ScratchboxRunParam(runner.RunParam):
    def __init__(self, root, out):
        super(ScratchboxRunParam, self).__init__(root, out)
        self.interp = ['/scratchbox/login', '-d', str(root)] + self.interp


if __name__ == '__main__':
    opts, args = runner.util.parser.parse_args()
    runner.main(opts, args, ScratchboxRunParam)
