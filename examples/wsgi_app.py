import guv

guv.monkey_patch()
import json

import bottle

import guv.wsgi
import logger

logger.configure()

app = bottle.Bottle()


@app.route('/')
def index():
    data = json.dumps({'status': True})
    return data


if __name__ == '__main__':
    server_sock = guv.listen(('0.0.0.0', 8001))
    guv.wsgi.server(server_sock, app)
