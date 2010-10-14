# XXX ensure b value is as expected
# XXX add not assertions for op1
load_store = {
    'STR_ri': {'A':0, 'op1': 0x0, 'B': 0, 'imm': True},
    'STR_rr': {'A':1, 'op1': 0x0, 'B': 0, 'imm': False},
    'LDR_ri': {'A':0, 'op1': 0x1, 'B': 0, 'imm': True},
    'LDR_rr': {'A':1, 'op1': 0x1, 'B': 0, 'imm': False},
    'STRB_ri': {'A':0, 'op1': 0x4, 'B': 0, 'imm': True},
    'STRB_rr': {'A':1, 'op1': 0x4, 'B': 0, 'imm': False},
    'LDRB_ri': {'A':0, 'op1': 0x5, 'B': 0, 'imm': True},
    'LDRB_rr': {'A':1, 'op1': 0x5, 'B': 0, 'imm': False},
}

data_proc = {
    'AND_rr': {'op1':0x0, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'EOR_rr': {'op1':0x2, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'SUB_rr': {'op1':0x4, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'RSB_rr': {'op1':0x6, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'ADD_rr': {'op1':0x8, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'ADC_rr': {'op1':0xA, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'SBC_rr': {'op1':0xC, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'RSC_rr': {'op1':0xE, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'TST_rr': {'op1':0x11, 'op2':0, 'op3':0, 'result':False, 'base':True},
    'TEQ_rr': {'op1':0x13, 'op2':0, 'op3':0, 'result':False, 'base':True},
    'CMP_rr': {'op1':0x15, 'op2':0, 'op3':0, 'result':False, 'base':True},
    'CMN_rr': {'op1':0x17, 'op2':0, 'op3':0, 'result':False, 'base':True},
    'ORR_rr': {'op1':0x18, 'op2':0, 'op3':0, 'result':True, 'base':True},
    'MOV_rr': {'op1':0x1A, 'op2':0, 'op3':0, 'result':True, 'base':False},
    'LSL_ri': {'op1':0x1A, 'op2':0x0, 'op3':0, 'op2cond':'!0', 'result':False, 'base':True},
    'LSR_ri': {'op1':0x1A, 'op2':0, 'op3':0x1, 'op2cond':'', 'result':False, 'base':True},
    'ASR_ri': {'op1':0x1A, 'op2':0, 'op3':0x2, 'op2cond':'', 'result':False, 'base':True},
    #'RRX_ri': {'op1':0x1A, 'op2':0, 'op3':0x3, 'op2cond':'0', 'result':False, 'base':True},
    'ROR_ri': {'op1':0x1A, 'op2':0x0, 'op3':0x3, 'op2cond':'!0', 'result':True, 'base':False},
}
