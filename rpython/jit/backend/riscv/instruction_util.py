#!/usr/bin/env python

def check_simm21_arg(imm):
    return imm >= -2**20 and imm <= 2**20 - 1 and imm & 0x1 == 0
