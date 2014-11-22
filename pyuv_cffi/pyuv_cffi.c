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
    uv_poll_t *handle = malloc(sizeof(uv_poll_t));
    uv_poll_init(loop, handle, fd);
    return handle;
}

void pyuv_poll_del(uv_poll_t *handle) {
    free(handle);
}
