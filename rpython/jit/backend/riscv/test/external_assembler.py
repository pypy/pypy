#!/usr/bin/env python

import os

from rpython.tool.udir import udir


class Asseumbler(object):
    asm_opts = '-march=rv64imafd'
    body = """
    .section .text
    .global _start
    .global main
_start:
    jal ra, main
    ebreak  # begin_tag
    ebreak  # begin_tag
    ebreak  # begin_tag
    ebreak  # begin_tag

main:
    %s

    jr ra   # end_tag
    ebreak  # end_tag
    ebreak  # end_tag
    ebreak  # end_tag
"""

    begin_tag = '\x73\x00\x10\x00' * 4
    end_tag = '\x67\x80\x00\x00' + '\x73\x00\x10\x00' * 3

    base_name = 'test_%d.asm'
    index = 0

    def __init__(self, instr):
        self.instr = instr
        self.file = udir.join(self.base_name % self.index)
        while self.file.check():
            self.index += 1
            self.file = udir.join(self.base_name % self.index)

    def extract(self):
        f = open("%s/a.out" % udir, 'rb')
        data = f.read()
        f.close()

        begin_pos = data.find(self.begin_tag)
        assert begin_pos >= 0
        begin_pos += len(self.begin_tag)
        end_pos = data.find(self.end_tag, begin_pos)
        assert end_pos >= 0

        return data[begin_pos:end_pos]

    def assemble(self, *args):
        res = self.body % (self.instr)
        self.file.write(res)
        os.system("as --fatal-warnings %s %s -o %s/a.out" %
                  (self.asm_opts, self.file, udir))


def assemble(instr):
    a = Asseumbler(instr)
    a.assemble(instr)
    return a.extract()
