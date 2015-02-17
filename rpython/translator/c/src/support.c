#include "common_header.h"
#include <src/support.h>
#include <src/exception.h>

/************************************************************/
/***  C header subsection: support functions              ***/

#include <stdio.h>
#include <stdlib.h>

/*** misc ***/

RPY_EXTERN
void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg) {
  fprintf(stderr,
          "PyPy assertion failed at %s:%ld:\n"
          "in %s: %s\n",
          filename, lineno, function, msg);
  abort();
}

RPY_EXTERN
void RPyAbort(void) {
  fprintf(stderr, "Invalid RPython operation (NULL ptr or bad array index)\n");
  abort();
}
