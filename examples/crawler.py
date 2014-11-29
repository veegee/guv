import guv

guv.monkey_patch()
import requests

def get_url(url):
    print('get_url()')
    return requests.get(url)

def main():
    urls = ['http://httpbin.org/delay/1'] * 10

    pool = guv.GreenPool()

    results = pool.imap(get_url, urls)
    for i, resp in enumerate(results):
        print('{}: done, length: {}'.format(i, len(resp.text)))


if __name__ == '__main__':
    main()
