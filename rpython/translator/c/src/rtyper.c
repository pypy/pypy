/************************************************************/
/***  C header subsection: tools for RTyper-aware code    ***/
#include "common_header.h"
#include "structdef.h"
#include "forwarddecl.h"
#include "preimpl.h"
#include <src/rtyper.h>

#include <stdlib.h>
#include <string.h>

#ifdef RPY_STM
#define __thread_if_stm  __thread
#else
#define __thread_if_stm  /* nothing */
#endif

static __thread_if_stm struct _RPyString_dump_t {
	struct _RPyString_dump_t *next;
	char data[1];
} *_RPyString_dump = NULL;

char *RPyString_AsCharP(RPyString *rps)
{
	Signed i, len = RPyString_Size(rps);
	struct _RPyString_dump_t *dump = \
			malloc(sizeof(struct _RPyString_dump_t) + len);
	if (!dump)
		return "(out of memory!)";
	dump->next = _RPyString_dump;
	_RPyString_dump = dump;
	/* can't use memcpy() in case of stm */
	for (i = 0; i < len; i++) {
	    dump->data[i] = rps->rs_chars.items[i];
            rpy_duck();
        }
	dump->data[len] = 0;
	return dump->data;
}

void RPyString_FreeCache(void)
{
	while (_RPyString_dump) {
		struct _RPyString_dump_t *dump = _RPyString_dump;
		_RPyString_dump = dump->next;
		free(dump);
	}
}
