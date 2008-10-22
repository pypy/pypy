import os
import sys
import py
import pdb
import time
from pypy.lang.gameboy.cpu import OP_CODES, FETCH_EXECUTE_OP_CODES
from pypy.lang.gameboy.ram import iMemory
from pypy.lang.gameboy.interrupt import Interrupt
from pypy.lang.gameboy.profiling.profiling_cpu import ProfilingCPU

PRINT_OPCODE_LABEL=False

def entry_point(argv=None):
    typical = False
    count = 100
    if argv is not None and len(argv) >= 1:
        if len(argv) >= 2:
            count = int(argv[2])
        if argv[1] == "0":
            run_all(count)
        elif argv[1] == "1":
            run_typical(count)
        elif argv[1] == "2":
            run_each(count)
        elif argv[1] == "3":
            run_all_first_order(count)
        elif argv[1] == "4":
            run_all_second_order(count)
    else:
        run_all(count)
    return 1
    
    
def run_typical(count):
    print run(TYPICAL_LIST, count)
    
def run_all(count):
    print run(FULL_LIST, count)
    
def run_each(count):
    run_each_first_order(count)
    run_each_second_order(count)
    
def run_each_first_order(count):
    forbidden = [0xCB, 211]
    op_codes = [0x00]*2
    for i in range(0xFF):
        if i not in forbidden and OP_CODES[i] is not None:
            op_codes[0] = i
            if PRINT_OPCODE_LABEL:
                print i, ":", run(op_codes, count)
            else:
                print  run(op_codes, count)
    
def run_each_second_order(count):
    op_codes = [0xCB]*2
    for i in range(0xFF):
        op_codes[1] = i
        if PRINT_OPCODE_LABEL:
            print  "0xCB :", i, ":" , run(op_codes, count)
        else:
            print  run(op_codes, count)
    
def run_all_first_order(count):
    print run(FIRST_ORDER_LIST, count)
    
def run_all_second_order(count):
    print run(SECOND_ORDER_LIST, count)
    
    
def run(op_codes, count):
    cpu = ProfilingCPU(Interrupt(), iMemory())
    
    start_time = time.time()
    for i in range(count):
        cpu.run(op_codes)
    end_time = time.time()
    return end_time - start_time


def create_all_first_order():
    list = []
    forbidden = [0xCB, 211]
    for i in range(0xFF):
        if i not in forbidden and OP_CODES[i] is not None:
            list.append(i)
    return list

def create_all_second_order():
    list = []
    forbidden = []
    for i in range(0xFF):
        if i not in forbidden:
            list.append(0xCB)
            list.append(i)
        
    return list


def create_typical_op_codes():
    list = []
    append_to_opcode_list(list, 0xff, 911896);
    append_to_opcode_list(list, 0x20, 260814);
    append_to_opcode_list(list, 0xf0, 166327);
    append_to_opcode_list(list, 0xfe, 166263);
    append_to_opcode_list(list, 0x13, 74595);
    append_to_opcode_list(list, 0x12, 74582);
    append_to_opcode_list(list, 0x2a, 72546);
    append_to_opcode_list(list, 0xb1, 70495);
    append_to_opcode_list(list, 0xb, 70487);
    append_to_opcode_list(list, 0x78, 70487);
    append_to_opcode_list(list, 0x5, 24998);
    append_to_opcode_list(list, 0x32, 24962);
    append_to_opcode_list(list, 0x38, 4129);
    append_to_opcode_list(list, 0xd, 3170);
    append_to_opcode_list(list, 0x22, 1034);
    append_to_opcode_list(list, 0xcd, 308);
    append_to_opcode_list(list, 0x21, 294);
    append_to_opcode_list(list, 0xc9, 292);
    append_to_opcode_list(list, 0xf5, 284);
    append_to_opcode_list(list, 0xf1, 282);
    append_to_opcode_list(list, 0xc3, 277);
    append_to_opcode_list(list, 0x77, 275);
    append_to_opcode_list(list, 0x7e, 261);
    append_to_opcode_list(list, 0x3c, 260);
    append_to_opcode_list(list, 0xe0, 88);
    append_to_opcode_list(list, 0x3e, 55);
    append_to_opcode_list(list, 0xea, 47);
    append_to_opcode_list(list, 0xaf, 45);
    append_to_opcode_list(list, 0x70, 40);
    append_to_opcode_list(list, 0x7d, 40);
    return list

def append_to_opcode_list(list, op_code, count):
    for i in range(count):
        list.append(op_code)
    
TYPICAL_LIST = create_typical_op_codes()

FIRST_ORDER_LIST = create_all_first_order()
SECOND_ORDER_LIST = create_all_second_order()
FULL_LIST = []
FULL_LIST.extend(FIRST_ORDER_LIST)
FULL_LIST.extend(SECOND_ORDER_LIST)

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

def test_target():
    entry_point()


if __name__ == '__main__':
    entry_point(sys.argv)
    