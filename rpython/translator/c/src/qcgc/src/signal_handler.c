#include "signal_handler.h"

#include <signal.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>

#include "arena.h"
#include "allocator.h"

QCGC_STATIC void handle_error(int signo, siginfo_t *siginfo, void *context);
QCGC_STATIC bool is_stack_overflow(void *addr);
QCGC_STATIC bool is_in_arena(void *addr);

void setup_signal_handler(void) {
	struct sigaction sa;

	sa.sa_handler = NULL;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = SA_SIGINFO | SA_NODEFER;
	sa.sa_sigaction = &handle_error;

	if (sigaction(SIGSEGV, &sa, NULL) < 0) {
		perror("sigaction");
		abort();
	}
}

QCGC_STATIC void handle_error(int signo, siginfo_t *siginfo, void *context) {
	UNUSED(signo);
	UNUSED(context);

	if (is_stack_overflow(siginfo->si_addr)) {
		fprintf(stderr, "Stack overflow: Too many root objects\n");
	} else if (is_in_arena(siginfo->si_addr)) {
		fprintf(stderr, "Internal segmentation fault: accessing %p\n",
				siginfo->si_addr);
	} else {
		fprintf(stderr, "External segmentation fault: accessing %p\n",
				siginfo->si_addr);
	}
	exit(EXIT_FAILURE);
}

QCGC_STATIC bool is_stack_overflow(void *addr) {
	void *shadow_stack_end = (void *)(_qcgc_shadowstack.base +
		QCGC_SHADOWSTACK_SIZE);
	return (addr >= shadow_stack_end && addr < shadow_stack_end + 8192);
}

QCGC_STATIC bool is_in_arena(void *addr) {
	arena_t *arena = qcgc_arena_addr((cell_t *) addr);
	size_t count = qcgc_allocator_state.arenas->count;
	for (size_t i = 0; i < count; i++) {
		if (arena == qcgc_allocator_state.arenas->items[i]) {
			return true;
		}
	}
	return false;
}
