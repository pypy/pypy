#include <iostream>
#include <iomanip>
#include <sys/times.h>
#include <unistd.h>

#include "example01.h"

static double gTicks = 0;

double get_cputime() {
   struct tms cpt;
   times(&cpt);
   return (double)(cpt.tms_utime+cpt.tms_stime) / gTicks;
}

int g() {
    int i = 0;
    for ( ; i < 10000000; ++i)
        ;
    return i;
}

int f() {
    int i = 0;
    example01 e;
    for ( ; i < 10000000; ++i)
        e.addDataToInt(i);
    return i;
}


int main() {
    gTicks = (double)sysconf(_SC_CLK_TCK);
    double t1 = get_cputime();
    g();
    double t2 = get_cputime();
    f();
    double t3 = get_cputime();

    std::cout << std::setprecision( 8 );
    std::cout << (t3 - t2) << " " << (t2 - t1) << std::endl;
    std::cout << (t3-t2) - (t2 - t1) << std::endl;

    return 0;
}
