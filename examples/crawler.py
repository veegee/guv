import guv
guv.monkey_patch()

import requests


def get_url(url):
    print('get_url({})'.format(url))
    return requests.get(url)


def main():
    urls = ['http://reddit.com'] * 10
    urls += ['https://twitter.com'] * 10

    pool = guv.GreenPool()

    results = pool.starmap(get_url, zip(urls))
    for i, resp in enumerate(results):
        print('{}: done, length: {}'.format(i, len(resp.text)))


if __name__ == '__main__':
    main()
