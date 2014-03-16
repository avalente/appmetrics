""" simple bottle application to show appmetrics usage. """

# a couple of endpoints are defined and a couple of metrics
# measuring throughput and latency for each endpoint plus one
# for the global throughput
# 
# of course, bottle must be installed (pip install bottle)
# Example:
#

# $ python examples/webapp_bottle.py 
# Bottle v0.12.5 server starting up (using WSGIRefServer(threaded=True))...
# Listening on http://127.0.0.1:5000/
# Hit Ctrl-C to quit.

#
# $ curl http://localhost:5000/_app-metrics/
# ["factorial-latency", "factorial-tp", "primality-latency", "primality-tp", "throughput"]
# 
# $ curl http://localhost:5000/is-prime/1234567893571
# {
#   "is_prime": true
# }
# 
# $ curl http://localhost:5000/factorial/200
# {
#   "factorial": "788657867364790503552363213932185062295135977687173263294742533244359449963403342920304284011984623904177212138919638830257642790242637105061926624952829931113462857270763317237396988943922445621451664240254033291864131227428294853277524242407573903240321257405579568660226031904170324062351700858796178922222789623703897374720000000000000000000000000000000000000000000000000"
# }
# 
# $ curl http://localhost:5000/_app-metrics/throughput
# {"count": 2, "five": 0.0033057092356765017, "mean": 0.10312407653907245, "fifteen": 0.0011080303990206543, "day": 1.1573739182546561e-05, "one": 0.015991117074135343}

import json
from bottle import route, run, app, response

from appmetrics import metrics

@route('/factorial/<n:int>')
@metrics.with_meter("factorial-tp")
@metrics.with_histogram("factorial-latency")
@metrics.with_meter("throughput")
def factorial(n):
    f = 1
    for i in xrange(2, n+1):
        f *= i
    response.content_type = "application/json"
    return json.dumps(dict(factorial=str(f)))


@route('/is-prime/<n:int>')
@metrics.with_meter("primality-tp")
@metrics.with_histogram("primality-latency")
@metrics.with_meter("throughput")
def is_prime(n):
    result = True

    if n % 2 == 0:
        result = False
    else:
        for i in xrange(3, int(n**0.5)+1, 2):
            if n % i == 0:
                result = False

    response.content_type = "application/json"
    return json.dumps(dict(is_prime=result))


if __name__ == '__main__':
    from appmetrics.wsgi import AppMetricsMiddleware
    myapp = AppMetricsMiddleware(app())
    run(app=myapp, port=5000, threaded=True, debug=True)
