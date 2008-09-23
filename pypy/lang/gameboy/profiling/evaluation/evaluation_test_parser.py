#!/bin/python

import operator

def add_rank(file):
    lines = open(file).readlines()
    lastRank = -1;
    for line in lines:
        pos = line.find(":")
        if pos > 0:
            opcode = line[:pos].strip()
            add_rank_opcode(line[:pos], int(line[pos+2:]))
        
            
    
def add_rank_opcode(opcode, count):
    if not op_codes.has_key(opcode):
        op_codes[opcode] = count
    else:
        op_codes[opcode] += count
    

def print_sorted(table):
    sorted_op_codes = sorted(op_codes.items(), key=operator.itemgetter(1))
    sorted_op_codes.reverse()
    for op_code in sorted_op_codes:
        print "%9s : %s" % (op_code[0], op_code[1])
    
# --------------------------------------
files = ["superMario.txt", "rom9.txt", "megaman.txt", "kirbysDreamland.txt"]

op_codes = {}
fetch_op_codes = [0] * 0xFF

for file in files:
    add_rank("logs/"+file)
    
print_sorted(op_codes)
    