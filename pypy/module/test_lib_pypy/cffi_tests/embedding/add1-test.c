#include <stdio.h>

extern int add1(int, int);


int main(void)
{
    int x, y;
    x = add1(40, 2);
    y = add1(100, -5);
    printf("got: %d %d\n", x, y);
    return 0;
}
