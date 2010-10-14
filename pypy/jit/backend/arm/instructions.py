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
