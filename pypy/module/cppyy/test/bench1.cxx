#include <iostream>
#include <iomanip>
#include <time.h>
#include <unistd.h>

#include "example01.h"

static const int NNN = 10000000;


int cpp_loop_offset() {
    int i = 0;
    for ( ; i < NNN*10; ++i)
        ;
    return i;
}

int cpp_bench1() {
    int i = 0;
    example01 e;
    for ( ; i < NNN*10; ++i)
        e.addDataToInt(i);
    return i;
}


int main() {

    clock_t t1 = clock();
    cpp_loop_offset();
    clock_t t2 = clock();
    cpp_bench1();
    clock_t t3 = clock();

    std::cout << std::setprecision(8)
              << ((t3-t2) - (t2-t1))/((double)CLOCKS_PER_SEC*10.) << std::endl;

    return 0;
}
