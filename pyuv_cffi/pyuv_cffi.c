/**
 * Custom C functions for using libuv with CFFI
 */
#include <stdio.h>
#include <stdlib.h>
#include <uv.h>

#if UV_VERSION_MAJOR < 1
#error "libuv >= 1.0.0 is required"
#endif

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
