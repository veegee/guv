import json


def create_response(s):
    resp = '''
HTTP/1.1 200 OK
Connection: close
Content-Type: text/plain; charset=utf-8
Content-Length: {length}

{data}
'''.format(length=len(s), data=s)

    resp = '\r\n'.join(resp.strip().split('\n'))
    return resp


def create_example():
    s = create_response(json.dumps({'status': True}))
    return bytes(s, 'UTF-8')
