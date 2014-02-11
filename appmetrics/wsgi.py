##  Module wsgi.py
##
##  Copyright (c) 2014 Antonio Valente <y3sman@gmail.com>
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##  http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.


"""
WSGI middleware
"""

import logging
from cgi import escape
import json

from . import metrics, exceptions


log = logging.getLogger("appmetrics.wsgi")


class AppMetricsMiddleware(object):
    """
    WSGI middleware for AppMetrics

    Usage:

    Instantiate me with the wrapped WSGI application. This middleware looks for request paths starting
    with "/_app-metrics": if not found, the wrapped application is called. The following resources are defined:
    - /_app-metrics:
        - GET: return the list of the registered metrics
    - /_app-metrics/<name>:
        - GET: return the value of the given metric or 404
        - PUT: create a new metric with the given name. The body must be a JSON object with a
               mandatory attribute named "type" which must be one of the metrics types allowed,
               by the "metrics.METRIC_TYPES" dictionary, while the other attributes are
               passed to the new_<type> function as keyword arguments.
               Request's content-type must be "application/json"
        - POST: add a new value to the metric. The body must be a JSON object with a mandatory
                attribute named "value": the notify function will be called with the given value.
                Other attributes are ignored.
                Request's content-type must be "application/json"

    The root can be different from "/_app-metrics", you can set it on middleware constructor.
    """

    statuses = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        411: "Length Required",
        415: "Unsupported Media Type",
        500: "Internal Server Error",
    }

    def __init__(self, app, root="_app-metrics", extra_headers=None):
        """
        parameters:
        - app: wrapped WSGI application
        - root: path root to look for
        - extra_headers: extra headers that will be appended to the return headers
        """
        self.app = app
        self.root = (root if root.startswith("/") else "/"+root).strip()
        self.extra_headers = extra_headers or {}

    def match(self, path):
        """Return the actual request path (starting from the root) or None if not matched"""

        if path.strip() == self.root:
            return ""

        if path.startswith(self.root):
            path = path[len(self.root):]
            if path.startswith('/'):
                return path

        return None

    def __call__(self, environ, start_response):
        """WSGI application interface"""

        path = self.match(environ['PATH_INFO'])
        if path is None:
            # the request did not match, go on with wsgi stack
            return self.app(environ, start_response)
        else:
            # extract the method
            method = environ['REQUEST_METHOD'].upper()

            # dispatch the call
            handler = AppMetricsHandler(environ)
            status, body = handler.handle(method, path)

            # handle the response status
            if status not in self.statuses:
                status = 500

            headers = {'Content-Type': 'application/json'}
            headers.update(self.extra_headers)

            # if not 200, build a status page
            if status != 200 and not body:
                body = self.error_body(status)
                headers['Content-Type'] = 'text/html'
            elif status != 200:
                body = json.dumps(body)

            headers = headers.items()

            # build status line
            status_text = self.statuses[status]
            status_string = "{} {}".format(status, status_text)

            # encode the body if needed and add the content-length
            if isinstance(body, unicode):
                body = body.encode('utf8')
            size = len(body)
            headers = headers + [('Content-Length', str(size))]

            # start response
            start_response(status_string, headers)

            return [body]

    def error_body(self, code):
        """build an html page for the given error code"""

        name = self.statuses[code]
        html = (
            u'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
            u'<html><head><title>{code} {name}</title></head>\n'
            u'<body><h1>{name}</h1></body></html>\n'
        )
        return html.format(code=code, name=escape(name))


class AppMetricsHandler(object):
    """Request handler for the WSGI middleware"""

    def __init__(self, environ):
        self.environ = environ

    def handle(self, method, path):
        if not path:
            status, data = self.handle_list(method)
        else:
            status, data = self.handle_metric(method, path[1:])

        return status, data

    def handle_list(self, method):
        if method != "GET":
            return 405, ""
        return 200, json.dumps(metrics.metrics())

    def handle_metric(self, method, name):
        if method == "GET":
            return self.return_metric(name)

        if method == "DELETE":
            res = metrics.delete_metric(name)

            return 200, "deleted" if res else "not deleted"

        elif method in ("PUT", "POST"):
            # get content length
            length = self.environ.get('CONTENT_LENGTH')
            if not length:
                return 411, None
            try:
                length = int(length)
            except Exception:
                log.debug("Invalid content-length: %s" % length)
                return 400, None

            # get content type
            ctype = self.environ.get('CONTENT_TYPE')
            if not ctype:
                return 415, None
            ctype = ctype.split(";")
            if ctype[0].strip().lower() != "application/json":
                return 415, None

            # get content data
            body = self.environ['wsgi.input'].read(length)
            try:
                body = json.loads(body)
            except Exception as e:
                log.debug("Invalid body: %s", e)
                return 400, "invalid json"

            # dispatch on method
            if method == "PUT":
                return self.add_metric(name, body)
            else:
                return self.add_value(name, body)
        else:
            return 405, None

    def add_metric(self, name, data):
        type_ = data.pop('type', None)
        if not type_:
            return 400, "metric type not provided"

        metric_type = metrics.METRIC_TYPES.get(type_)

        if not metric_type:
            return 400, "invalid metric type: {!r}".format(type_)

        try:
            metric_type(name, **data)
        except exceptions.AppMetricsError as e:
            return 400, "can't create metric {}({!r}): {}".format(type_, name, e)
        except Exception as e:
            log.debug(str(e), exc_info=True)
            return 400, "can't create metric {}({!r})".format(type_, name)

        return 200, ""

    def add_value(self, name, data):
        value = data.pop('value', None)
        if value is None:
            return 400, "metric value not provided"

        try:
            metric = metrics.metric(name)
        except KeyError:
            return 404, None

        metric.notify(value)

        return 200, ""

    def return_metric(self, name):
        try:
            metric = metrics.metric(name)
        except KeyError:
            return 404, "No such metric: %r" % name

        return 200, json.dumps(metric.get())