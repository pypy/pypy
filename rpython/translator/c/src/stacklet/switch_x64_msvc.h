/* The actual stack saving function, which just stores the stack,
 * this declared in an .asm file
 */
extern void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra);

