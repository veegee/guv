typedef enum {
    UV_RUN_DEFAULT = 0,
    UV_RUN_ONCE,
    UV_RUN_NOWAIT
} uv_run_mode;

enum uv_poll_event {
    UV_READABLE = 1,
    UV_WRITABLE = 2
};


// handle structs and types
struct uv_loop_s {...;};
struct uv_handle_s {...;};
struct uv_idle_s {...;};
struct uv_prepare_s {...;};
struct uv_timer_s {...;};
struct uv_signal_s {...;};
struct uv_poll_s {...;};

typedef struct uv_loop_s uv_loop_t;
typedef struct uv_handle_s uv_handle_t;
typedef struct uv_idle_s uv_idle_t;
typedef struct uv_prepare_s uv_prepare_t;
typedef struct uv_timer_s uv_timer_t;
typedef struct uv_signal_s uv_signal_t;
typedef struct uv_poll_s uv_poll_t;

typedef void (*uv_close_cb)(uv_handle_t *handle);
typedef void (*uv_idle_cb)(uv_idle_t* handle);
typedef void (*uv_prepare_cb)(uv_prepare_t* handle);
typedef void (*uv_poll_cb)(uv_poll_t *handle, int status, int events);
typedef void (*uv_timer_cb)(uv_timer_t *handle);
typedef void (*uv_signal_cb)(uv_signal_t *handle, int signum);


// loop functions
uv_loop_t *uv_default_loop();
int uv_loop_init(uv_loop_t* loop);
int uv_loop_alive(const uv_loop_t *loop);
int uv_run(uv_loop_t*, uv_run_mode mode);
void uv_stop(uv_loop_t*);


// handle functions
uv_handle_t *cast_handle(void *handle);

void uv_ref(uv_handle_t *);
void uv_unref(uv_handle_t *);
int uv_has_ref(const uv_handle_t *);
void uv_close(uv_handle_t *handle, uv_close_cb close_cb);
int uv_is_active(const uv_handle_t *handle);
int uv_is_closing(const uv_handle_t *handle);


// idle functions
int uv_idle_init(uv_loop_t*, uv_idle_t* idle);
int uv_idle_start(uv_idle_t* idle, uv_idle_cb cb);
int uv_idle_stop(uv_idle_t* idle);


// prepare functions
int uv_prepare_init(uv_loop_t*, uv_prepare_t* prepare);
int uv_prepare_start(uv_prepare_t* prepare, uv_prepare_cb cb);
int uv_prepare_stop(uv_prepare_t* prepare);


// timer functions
int uv_timer_init(uv_loop_t*, uv_timer_t* handle);
int uv_timer_start(uv_timer_t *handle, uv_timer_cb cb, uint64_t timeout, uint64_t repeat);
int uv_timer_stop(uv_timer_t *handle);
int uv_timer_again(uv_timer_t *handle);
void uv_timer_set_repeat(uv_timer_t *handle, uint64_t repeat);
uint64_t uv_timer_get_repeat(const uv_timer_t *handle);


// signal functions
int uv_signal_init(uv_loop_t* loop, uv_signal_t* handle);
int uv_signal_start(uv_signal_t *handle, uv_signal_cb signal_cb, int signum);
int uv_signal_stop(uv_signal_t *handle);


// poll functions
int uv_poll_init(uv_loop_t* loop, uv_poll_t* handle, int fd);
int uv_poll_start(uv_poll_t *handle, int events, uv_poll_cb cb);
int uv_poll_stop(uv_poll_t *handle);
