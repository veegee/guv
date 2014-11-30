import logging
import logger
logger.configure()

import guv
guv.monkey_patch()

import requests

log = logging.getLogger()


def get_url(url):
    print('get_url({})'.format(url))
    return requests.get(url)


def main():
    urls = ['http://reddit.com'] * 3
    urls += ['https://twitter.com'] * 3

    pool = guv.GreenPool()

    results = pool.imap(get_url, urls)
    for i, resp in enumerate(results):
        print('{}: done, length: {}'.format(i, len(resp.text)))


if __name__ == '__main__':
    main()
