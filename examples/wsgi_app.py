import json
import time

import bottle

import guv
import guv.wsgi
import logger

logger.configure()

app = bottle.Bottle()


@app.route('/')
def index():
    time.sleep(0.2)
    data = json.dumps({'status': True})
    return data


if __name__ == '__main__':
    server_sock = guv.listen(('0.0.0.0', 8001))
    guv.wsgi.server(server_sock, app)
