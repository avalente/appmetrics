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

import logging, logging.config
import json

import werkzeug

from . import metrics, exceptions, py3comp


log = logging.getLogger("appmetrics.wsgi")


class AppMetricsMiddleware(object):
    """
    WSGI middleware for AppMetrics

    Usage:

    Instantiate me with the wrapped WSGI application. This middleware looks for request paths starting
    with "/_app-metrics": if not found, the wrapped application is called. The following resources are defined:

    ``/_app-metrics/metrics``
      - **GET**: return the list of the registered metrics
    ``/_app-metrics/metrics/<name>``
      - **GET**: return the value of the given metric or ``404``.
      - **PUT**: create a new metric with the given name. The body must be a ``JSON`` object with a
        mandatory attribute named ``"type"`` which must be one of the metrics types allowed,
        by the ``"metrics.METRIC_TYPES"`` dictionary, while the other attributes are
        passed to the ``new_<type>`` function as keyword arguments.
        Request's ``content-type`` must be ``"application/json"``.
      - **POST**: add a new value to the metric. The body must be a ``JSON`` object with a mandatory
        attribute named ``"value"``: the notify method will be called with the given value.
        Other attributes are ignored.
        Request's ``content-type`` must be ``"application/json"``.
      - **DELETE**: remove the metric with the given name. Return "deleted" or "not deleted".
    ``/_app-metrics/tags``
      - **GET**: return the list of registered tags
    ``/_app-metrics/tags/<name>``
      - **GET**: return the metrics tagged with the given tag. If the value of the ``GET`` parameter ``"expand"``
        is ``"true"``, a JSON object is returned, with the name of each tagged metric as keys and corresponding values.
        If it is ``"false"`` or not provided, the list of metric names is returned.
        Return a ``404`` if the tag does not exist
    ``/_app-metrics/tags/<tag_name>/<metric_name>``
      - **PUT**: tag the metric named ``<metric_name>`` with ``<tag_name>``. Return a ``400`` if the given metric
        does not exist.
      - **DELETE**: remove the tag ``<tag_name>`` from ``<metric_name>``. Return "deleted" or "not deleted". If
        ``<tag_name>`` is no longer used, it gets implicitly removed.


    The root can be different from "/_app-metrics", you can set it on middleware constructor.
    """

    def __init__(self, app, root="_app-metrics", extra_headers=None, mimetype="application/json"):
        """
        parameters:
        - app: wrapped WSGI application
        - root: path root to look for
        - extra_headers: extra headers that will be appended to the return headers
        """
        self.app = app
        self.root = "/" + root.strip("/").strip()
        self.extra_headers = extra_headers or {}
        self.mimetype = mimetype

        self.url_map = werkzeug.routing.Map([
            werkzeug.routing.Submount(self.root, [
                werkzeug.routing.Rule("/metrics", endpoint=handle_metrics_list, methods=['GET']),
                werkzeug.routing.Rule("/metrics/<name>", endpoint=handle_metric_show, methods=['GET']),
                werkzeug.routing.Rule("/metrics/<name>", endpoint=handle_metric_new, methods=['PUT']),
                werkzeug.routing.Rule("/metrics/<name>", endpoint=handle_metric_update, methods=['POST']),
                werkzeug.routing.Rule("/metrics/<name>", endpoint=handle_metric_delete, methods=['DELETE']),
                werkzeug.routing.Rule("/tags", endpoint=handle_tags_list, methods=['GET']),
                werkzeug.routing.Rule("/tags/<tag_name>", endpoint=handle_tag_show, methods=['GET']),
                werkzeug.routing.Rule("/tags/<tag_name>/<metric_name>", endpoint=handle_tag_add, methods=['PUT']),
                werkzeug.routing.Rule("/tags/<tag_name>/<metric_name>", endpoint=handle_untag, methods=['DELETE']),
            ])
        ])

    def get_response(self, body, code, headers=None):
        if headers is None:
            headers = []
        headers = dict(headers).copy()
        headers.update(self.extra_headers)
        return werkzeug.wrappers.Response(body, code, headers.items(), self.mimetype)

    def jsonize_error(self, exception, environ):
        return self.get_response(json.dumps(exception.description), exception.code, exception.get_headers(environ))

    def __call__(self, environ, start_response):
        """WSGI application interface"""

        urls = self.url_map.bind_to_environ(environ)

        try:
            endpoint, args = urls.match()
        except werkzeug.exceptions.NotFound:
            # the request did not match, go on with wsgi stack
            return self.app(environ, start_response)

        except werkzeug.exceptions.HTTPException as e:
            response = self.jsonize_error(e, environ)

        else:
            request = werkzeug.wrappers.Request(environ, populate_request=False)
            try:
                body = endpoint(request, **args)
                response = self.get_response(body, 200)
            except werkzeug.exceptions.HTTPException as e:
                response = self.jsonize_error(e, environ)

            except Exception as e:
                log.debug("Unhandled exception: %s", e, exc_info=True)
                response = self.get_response("Internal Server Error", 500)

        return response(environ, start_response)


def get_body(request):
    # get content type
    ctype = request.mimetype
    if not ctype or ctype != "application/json":
        raise werkzeug.exceptions.UnsupportedMediaType()

    # get content data
    try:
        return py3comp.json_load(request.stream, request.charset)
    except ValueError as e:
        log.debug("Invalid body: %s", e)
        raise werkzeug.exceptions.BadRequest(description="invalid json")


def handle_metrics_list(request):
    return json.dumps(metrics.metrics())


def handle_metric_show(request, name):
    try:
        metric = metrics.metric(name)
    except KeyError:
        raise werkzeug.exceptions.NotFound(("No such metric: {!r}".format(name)))

    return json.dumps(metric.get())


def handle_metric_delete(request, name):
    res = metrics.delete_metric(name)

    return "deleted" if res else "not deleted"


def handle_metric_new(request, name):
    data = get_body(request)

    type_ = data.pop('type', None)
    if not type_:
        raise werkzeug.exceptions.BadRequest(description="metric type not provided")

    metric_type = metrics.METRIC_TYPES.get(type_)

    if not metric_type:
        raise werkzeug.exceptions.BadRequest("invalid metric type: {!r}".format(type_))

    try:
        metric_type(name, **data)
    except exceptions.AppMetricsError as e:
        raise werkzeug.exceptions.BadRequest("can't create metric {}({!r}): {}".format(type_, name, e))
    except Exception as e:
        log.debug(str(e), exc_info=True)
        raise werkzeug.exceptions.BadRequest("can't create metric {}({!r})".format(type_, name))

    return ""


def handle_metric_update(request, name):
    data = get_body(request)

    value = data.pop('value', None)
    if value is None:
        raise werkzeug.exceptions.BadRequest("metric value not provided")

    try:
        metric = metrics.metric(name)
    except KeyError:
        raise werkzeug.exceptions.NotFound()

    metric.notify(value)

    return ""


def handle_tags_list(request):
    return json.dumps(sorted(metrics.tags().keys()))


def handle_tag_show(request, tag_name):
    all_tags = metrics.tags()
    if tag_name not in all_tags:
        raise werkzeug.exceptions.NotFound(description="no such tag: {!r}".format(tag_name))

    if request.args.get('expand', 'false') == 'true':
        return json.dumps(metrics.metrics_by_tag(tag_name))
    else:
        return json.dumps(sorted(all_tags[tag_name]))


def handle_tag_add(request, tag_name, metric_name):
    try:
        metrics.tag(metric_name, tag_name)
    except metrics.InvalidMetricError as e:
        raise werkzeug.exceptions.BadRequest(description=str(e))

    return ""


def handle_untag(request, tag_name, metric_name):
    res = metrics.untag(metric_name, tag_name)

    return "deleted" if res else "not deleted"


# useful to run standalone with werkzeug's server:
# $ python -m werkzeug.serving appmetrics.wsgi.standalone_app
# * Running on http://127.0.0.1:5000/

standalone_app = AppMetricsMiddleware(werkzeug.exceptions.NotFound(), "")
