/**
 * Custom C functions for using libuv with CFFI
 *
 * This file mostly contains functions to allocate and deallocate memory. Since
 * `ffi.new()` needs to know the size of types, it is not possible to call it on
 * types like `uv_loop_t` or `uv_timer_t`. These `*_new()` and `*_del()`
 * functions solve this problem until I can find a way to do it "correctly" with
 * CFFI if possible.
 */
#include <stdio.h>
#include <stdlib.h>
#include <uv.h>


// loop functions
uv_loop_t *pyuv_loop_new(void) {
    uv_loop_t *loop = malloc(sizeof(uv_loop_t));
    uv_loop_init(loop);
    return loop;
}

void pyuv_loop_del(uv_loop_t *loop) {
    uv_loop_close(loop);
    free(loop);
}


// handle functions
/**
 * Create a `uv_handle_t *` from a `uv_?_t` specific handle type
 *
 * The purpose of this is to instantiate the `Handle` class and use base
 * `uv_handle_t` functions on any specific `uv_?_t` handle types. I couldn't
 * figure out how to use `ffi.cast` to get what I wanted, so that is the purpose
 * of this function.
 */
uv_handle_t *cast_handle(void *handle) {
    return (uv_handle_t *)handle;
}


// timer functions
uv_timer_t *pyuv_timer_new(uv_loop_t *loop) {
    uv_timer_t *timer_h = malloc(sizeof(uv_timer_t));
    uv_timer_init(loop, timer_h);
    return timer_h;
}

void pyuv_timer_del(uv_timer_t *timer_h) {
    free(timer_h);
}

// signal functions
uv_signal_t *pyuv_signal_new(uv_loop_t *loop) {
    uv_signal_t *sig_h = malloc(sizeof(uv_signal_t));
    uv_signal_init(loop, sig_h);
    return sig_h;
}

void pyuv_signal_del(uv_signal_t *sig_h) {
    free(sig_h);
}

// poll functions
uv_poll_t *pyuv_poll_new(uv_loop_t *loop, int fd) {
    uv_poll_t *poll_h = malloc(sizeof(uv_poll_t));
    uv_poll_init(loop, poll_h, fd);
    return poll_h;
}

void pyuv_poll_del(uv_poll_t *poll_h) {
    free(poll_h);
}
