import random


def fake_ua():
    a = ['(Windows NT 5.1; rv:40.0)', '(Windows NT 6.1; WOW64)', '(Windows NT 6.3; WOW64)',
         '(Windows NT 10.0; Win64; x64)', '(Macintosh; Intel Mac OS X 10_10_4)', '(Macintosh; Intel Mac OS X 10_9_5)',
         '(Macintosh; Intel Mac OS X 10_10_2)', '(iPad; CPU OS 8_1 like Mac OS X)']
    b = ['AppleWebKit/537.36 (KHTML, like Gecko)', 'Gecko/20100101', 'AppleWebKit/600.7.12 (KHTML, like Gecko)',
         'AppleWebKit/601.1.56 (KHTML, like Gecko)']
    c = ['Ubuntu Chromium/37.0.2062.94', 'Chrome/45.0.2454.85 Safari/537.36', 'Version/8.0.8 Safari/600.8.9',
         'Chrome/45.0.2454.85 Safari/537.36', 'Version/8.0 Mobile/12F69 Safari/600.1.4',
         'Version/7.0 Mobile/11D257 Safari/9537.53', 'Version/8.0 Mobile/12B440 Safari/600.1.4',
         'Chrome/39.0.2171.95 Safari/537.36']
    return 'Mozilla/5.0 ' + a[random.randint(0, len(a) - 1)] + ' ' + b[random.randint(0, len(b) - 1)] + ' ' + c[
        random.randint(0, len(c) - 1)]
