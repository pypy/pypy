import operator
from pypy.lang.gameboy import cpu
import pdb

DEBUG = True
DEBUG_PRINT_LOGS = True
# the following list contains all opcode which have been double checked
# meaning that the test have been reviewed and the code likewise.

op_codes               = [0] * (0xFF+1)
fetch_execute_op_codes = [0] * (0xFF+1)
COUNT                  = [0]
CHECKED_OP_CODES       = [0x00]
# load commands are checked + halt 0x76
CHECKED_OP_CODES += range(0x40, 0x80)
# and A_B to A_A
CHECKED_OP_CODES += range(0xA0, 0xA8)
# xor A_B to A_A
CHECKED_OP_CODES += range(0xA8, 0xB0)
# or A_B to A_A
CHECKED_OP_CODES += range(0xB0, 0xB8)
CHECKED_OP_CODES += [
    # double register fetch_nn load
    0x01, 0x11, 0x21, 0x31,
    # register fetch_nn load
    0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,
    # store_fetched_memory_in_a
    0xFA,
    # return contditional
    0xC0, 0xC8, 0xD0, 0xD8,
    # restart
    0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF,
    # increment double register
    0x03, 0x13, 0x23, 0x33,
    # decrement double register
    0x0B, 0x1B, 0x2B, 0x3B,
    # decrement register
    0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D,
    # increment register
    0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C,
    # enable interrupts
    0xFB,
    # disable interrupts
    0xF3,
    # return from interrupt
    0xD9,
    # svn comm a fetch
    0xC6,
    # conditional jump
    0xD2,
    # add_hl_bc up to add_hl_sp
    0x09, 0x19, 0x29, 0x39,
    # add_a_b thru add_a_A
    0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    # subtract with carry
    0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F,
    # xor a
    0xEE,
    # add with carry
    0x88,
    # sp = hl
    0xf9,
    # subtract a
    0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 
    # add with carry
    0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F,
    # compare a
    0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF,
    # conditional jumps
    0xC2, 0xCA, 0xD2, 0xCA,
    # complement a
    0x2F,
    # write_a_at_expaded_c_address
    0xe2,
    # conditional calls
    0xC4, 0xCC, 0xD4, 0xDC,
    # push Double Registers
    0xC5, 0xD5, 0xE5, 0xF5,
    # store_memory_at_de_in_a
    0x1A,
    # jump double fetch
    0xC3,
    # store_a_at_fetched_address
    0xEA,
    # relative jump
    0x18,
]

CHECKED_OP_CODES       = [0x00]
CHECKED_FETCH_OP_CODES = []
BAR_WIDTH = 79
PRINT_OPCODE=True

def log(opCode, is_fetch_execute=False):
    global COUNT, op_codes, fetch_execute_op_codes
    if DEBUG_PRINT_LOGS:
        print "=" * BAR_WIDTH
        if is_fetch_execute:
            print COUNT[0], "  FETCH EXEC: %i | %s  | %s" % (opCode, hex(opCode), resolve_fetch_opcode_name(opCode))
        else:
            print COUNT[0], "  EXEC: %i | %s | %s" % (opCode, hex(opCode), resolve_opcode_name(opCode))
        print "-" * BAR_WIDTH
    
    if is_fetch_execute:
        fetch_execute_op_codes[opCode ]+= 1
    else:
        op_codes[opCode] += 1
    COUNT[0] += 1
    #if COUNT % 1000 == 0:
    #    print "."
        
def resolve_opcode_name(opcode):
    method = cpu.OP_CODES[opcode].__name__
    if method == "<lambda>":
        try:
            functions = "[ "
            for func_closure in cpu.OP_CODES[opcode].func_closure:
                functions += func_closure.cell_contents.im_func.__name__+ ", ";
            return functions + "]";
        except:
            return cpu.OP_CODES[opcode].func_code.co_names;
    else:
        return method;
	
def resolve_fetch_opcode_name(opcode):
    method = cpu.OP_CODES[opcode].__name__
    if method == "<lambda>":
        pdb.set_trace()
    else:
        return method;
    

def print_results():
    global COUNT, op_codes, fetch_execute_op_codes
    
    print_function = (lambda x: "%4s" % hex(x))
    codes = zip(map( print_function, range(len(op_codes))), op_codes)
    
    print_function = (lambda x:  "%4s %4s" % (hex(x[0]), hex(x[1])))
    opcode_range = range(len(fetch_execute_op_codes))
    arguments = zip([0x83]  * len(fetch_execute_op_codes), opcode_range)
    fetch_exec_keys = map( print_function, opcode_range, arguments )
	# Append the fetchexecuted opcodes to the list
    codes.extend(zip(fetch_exec_keys, fetch_execute_op_codes))
    
    codes = sorted(codes, key=operator.itemgetter(1))
    for code in codes:
        if code[1] != 0:
            print "%8s \t %s" % (code[0], code[1])

    