def create_response(body, headers):
    """
    :type body: str
    :type headers: dict
    :rtype: str
    """
    final_headers = {
        'Connection': 'keep-alive',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Encoding': 'UTF-8'
    }

    final_headers.update(headers)

    lines = ['HTTP/1.1 200 OK']
    lines.extend(['%s: %s' % (k, v) for k, v in final_headers.items()])
    lines.append('Content-Length: %s' % len(body))

    resp = ('\r\n'.join(lines)).encode('latin-1')
    resp += ('\r\n\r\n' + body).encode(final_headers['Content-Encoding'])

    return resp
