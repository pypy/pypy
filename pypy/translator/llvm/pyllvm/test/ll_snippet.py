calc = """int %calc(int %n) {
    %tmp.0 = call int %add1(int %n)
    ret int %tmp.0
}
declare int %add1(int)"""

add1 = """int %add1(int %n) {
    %tmp.0 = add int %n, 1
    ret int %tmp.0
}"""

add1_version2 = """int %add1(int %n) {
    %tmp.0 = add int %n, 100 ;used for testing function replacement
    ret int %tmp.0
}"""

global_int_a_is_100 = """%a = global int 100"""

add1_to_global_int_a = """
int %add1_to_global_int_a() {
    %tmp.0 = load int* %a
    %tmp.1 = add int %tmp.0, 1
    store int %tmp.1, int* %a
    ret int %tmp.1
}"""

sub10_from_global_int_a = """int %sub10_from_global_int_a() {
    %tmp.0 = load int* %a
    %tmp.1 = sub int %tmp.0, 10
    store int %tmp.1, int* %a
    ret int %tmp.1
}"""
