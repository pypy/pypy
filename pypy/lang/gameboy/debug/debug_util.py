import operator
from pypy.lang.gameboy import cpu
import pdb

# ----------------------------------------------------------------------------
# This files contains some static function for print and loggin opcodes
#
# ----------------------------------------------------------------------------

DEBUG = False
DEBUG_PRINT_LOGS = True
op_codes               = [0] * (0xFF+1)
fetch_execute_op_codes = [0] * (0xFF+1)
COUNT                  = [0]

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

    
