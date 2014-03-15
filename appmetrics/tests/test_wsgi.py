import json
from cStringIO import StringIO

import mock
from nose.tools import assert_equal, assert_false, assert_is_instance, raises, assert_raises
import werkzeug, werkzeug.test

from .. import wsgi, metrics


def env(path, **kwargs):
    data = werkzeug.test.EnvironBuilder(path, environ_overrides=kwargs)
    return data.get_environ()


def req(body):
    data = werkzeug.test.EnvironBuilder(data=json.dumps(body), content_type="application/json")
    return data.get_request(cls=werkzeug.wrappers.Request)


def check_dispatching(mw, url, method, expected):
    urls = mw.url_map.bind_to_environ(env(url, REQUEST_METHOD=method))
    try:
        endpoint, _ = urls.match()
    except expected:
        pass
    except Exception:
        raise
    else:
        assert_equal(endpoint, expected)


def test_dispatching():
    tests = [
        ("/_app-metrics", 'GET', werkzeug.routing.RequestRedirect),
        ("/_app-metrics/", 'GET', wsgi.handle_metrics_list),
        ("/_app-metrics/", 'POST', werkzeug.exceptions.MethodNotAllowed),
        ("/_app-metrics/test", 'GET', wsgi.handle_metric_show),
        ("/_app-metrics/test", 'PUT', wsgi.handle_metric_new),
        ("/_app-metrics/test", 'POST', wsgi.handle_metric_update),
        ("/_app-metrics/test", 'DELETE', wsgi.handle_metric_delete),
        ("/_app-metrics/test", 'OPTIONS', werkzeug.exceptions.MethodNotAllowed),
        ("/_app-metrics/test/sub", 'GET', werkzeug.routing.NotFound),
    ]

    mw = wsgi.AppMetricsMiddleware(None)

    for url, method, expected in tests:
        yield lambda url, method: check_dispatching(mw, url, method, expected), url, method


def test_dispatching_root():
    tests = [
        ("/", 'GET', wsgi.handle_metrics_list),
        ("/", 'POST', werkzeug.exceptions.MethodNotAllowed),
        ("/test", 'GET', wsgi.handle_metric_show),
        ("/test", 'PUT', wsgi.handle_metric_new),
        ("/test", 'POST', wsgi.handle_metric_update),
        ("/test", 'DELETE', wsgi.handle_metric_delete),
        ("/test", 'OPTIONS', werkzeug.exceptions.MethodNotAllowed),
        ("/test/sub", 'GET', werkzeug.routing.NotFound),
        ]

    mw = wsgi.AppMetricsMiddleware(None, "")

    for url, method, expected in tests:
        yield lambda url, method: check_dispatching(mw, url, method, expected), url, method


class TestAppMetricsMiddleware(object):
    def setUp(self):
        self.app = mock.Mock()
        self.start_response = mock.Mock()

        self.patch = mock.patch('appmetrics.wsgi.handle_metrics_list')
        self.handler = self.patch.start()
        self.mw = wsgi.AppMetricsMiddleware(self.app)

    def tearDown(self):
        self.patch.stop()

    def test_call_not_matching(self):
        res = self.mw(env("/"), self.start_response)
        assert_equal(res, self.app.return_value)
        assert_false(self.start_response.called)
        assert_equal(
            self.app.call_args_list,
            [mock.call(env("/"), self.start_response)])

    def test_call_not_matching_2(self):
        res = self.mw(env("/test"), self.start_response)
        assert_equal(res, self.app.return_value)
        assert_false(self.start_response.called)
        assert_equal(
            self.app.call_args_list,
            [mock.call(env("/test"), self.start_response)])

    def test_call_not_matching_3(self):
        res = self.mw(env("/_app-metrics/test/sub"), self.start_response)
        assert_equal(res, self.app.return_value)
        assert_false(self.start_response.called)
        assert_equal(
            self.app.call_args_list,
            [mock.call(env("/_app-metrics/test/sub"), self.start_response)])

    def test_call_without_trailing_slash(self):
        self.handler.side_effect = ValueError()

        self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        assert_equal(
            self.start_response.call_args_list,
            [mock.call("301 MOVED PERMANENTLY", mock.ANY)]
        )

    def test_call_with_invalid_status(self):
        self.handler.side_effect = ValueError()

        self.mw(env("/_app-metrics/", REQUEST_METHOD='GET'), self.start_response)

        assert_equal(
            self.start_response.call_args_list,
            [mock.call("500 INTERNAL SERVER ERROR", mock.ANY)]
        )

    def test_call_with_error_implicit(self):
        self.handler.side_effect = werkzeug.exceptions.BadRequest()

        body = self.mw(env("/_app-metrics/", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps(werkzeug.exceptions.BadRequest.description)
        assert_equal(list(body), [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("400 BAD REQUEST", expected_headers)]
        )

    def test_call_with_error_explicit(self):
        self.handler.side_effect = werkzeug.exceptions.BadRequest(description="bad request received")

        body = self.mw(env("/_app-metrics/", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("bad request received")
        assert_equal(list(body), [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("400 BAD REQUEST", expected_headers)]
        )

    def test_call_ok(self):
        self.handler.return_value = json.dumps("results")

        body = self.mw(env("/_app-metrics/", REQUEST_METHOD='GET'), self.start_response)

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(self.handler.return_value)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("200 OK", expected_headers)]
        )

        assert_equal(list(body), [self.handler.return_value])


    def test_call_with_unicode(self):
        self.handler.return_value = unicode(json.dumps("results"))

        body = self.mw(env("/_app-metrics/", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("results")
        assert_equal(list(body), [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("200 OK", expected_headers)]
        )


class TestWSGIHandlers(object):
    def setUp(self):
        self.original_registry = metrics.REGISTRY
        metrics.REGISTRY.clear()

    def tearDown(self):
        metrics.REGISTRY.update(self.original_registry)

    @mock.patch('appmetrics.wsgi.metrics.metrics')
    def test_handle_metrics_list(self, metrics):
        metrics.return_value = ["test1", "test2"]

        assert_equal(wsgi.handle_metrics_list(mock.Mock()), '["test1", "test2"]')

    @mock.patch('appmetrics.wsgi.metrics.metric')
    def test_handle_metric_show(self, metric):
        metric().get.return_value = "this is a test"

        assert_equal(wsgi.handle_metric_show(mock.Mock(), "test"), '"this is a test"')

    @mock.patch('appmetrics.wsgi.metrics.metric')
    def test_handle_metric_show_not_found(self, metric):
        metric.side_effect = KeyError("key")

        with assert_raises(werkzeug.exceptions.NotFound) as exc:
            wsgi.handle_metric_show(mock.Mock(), "test")

        assert_equal(exc.exception.description, "No such metric: 'test'")

    def test_handle_metric_delete(self):
        with mock.patch.dict('appmetrics.metrics.REGISTRY', dict(test=mock.Mock())):
            res = wsgi.handle_metric_delete(mock.Mock(), "test")

            assert_equal(res, "deleted")
            assert_equal(metrics.REGISTRY, dict())

    def test_handle_metric_delete_not_found(self):
        with mock.patch.dict('appmetrics.metrics.REGISTRY', dict(none="test")):
            res = wsgi.handle_metric_delete(mock.Mock(), "test")

            assert_equal(res, "not deleted")
            assert_equal(metrics.REGISTRY, dict(none="test"))

    @raises(werkzeug.exceptions.UnsupportedMediaType)
    def test_get_body_no_content_type(self):
        request = werkzeug.wrappers.Request(dict(CONTENT_LENGTH=10))

        wsgi.get_body(request)

    @raises(werkzeug.exceptions.UnsupportedMediaType)
    def test_get_body_bad_content_type(self):
        request = werkzeug.wrappers.Request(dict(CONTENT_LENGTH=10, CONTENT_TYPE='text/html'))

        wsgi.get_body(request)

    def test_get_body_bad_content(self):
        env = {'CONTENT_LENGTH': 4, 'CONTENT_TYPE': "application/json", 'wsgi.input': StringIO("test wrong")}
        request = werkzeug.wrappers.Request(env)

        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.get_body(request)
        assert_equal(exc.exception.description, "invalid json")

    def test_get_body(self):
        env = {'CONTENT_LENGTH': 6, 'CONTENT_TYPE': "application/json", 'wsgi.input': StringIO('"test" with garbage')}
        request = werkzeug.wrappers.Request(env)

        assert_equal(wsgi.get_body(request), 'test')

    def test_handle_metric_new_missing_type(self):
        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_new(req(dict()), "test")
        assert_equal(exc.exception.description, "metric type not provided")

    def test_handle_metric_new_invalid_type(self):
        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_new(req(dict(type="xxx")), "test")
        assert_equal(exc.exception.description, "invalid metric type: u'xxx'")

    def test_handle_metric_new_app_error(self):
        wsgi.handle_metric_new(req(dict(type="gauge")), "test")

        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_new(req(dict(type="gauge")), "test")
        assert_equal(exc.exception.description, "can't create metric gauge('test'): Metric test already exists of type Gauge")

    def test_handle_metric_new_generic_error(self):
        new_gauge = mock.Mock(side_effect=ValueError("an error"))

        with mock.patch.dict('appmetrics.wsgi.metrics.METRIC_TYPES', gauge=new_gauge):
            with assert_raises(werkzeug.exceptions.BadRequest) as exc:
                wsgi.handle_metric_new(req(dict(type="gauge")), "test")
            assert_equal(exc.exception.description, "can't create metric gauge('test')")

    def test_handle_metric_new_metric(self):
        res = wsgi.handle_metric_new(req(dict(type="gauge")), "test")
        assert_equal(res, "")

        metric = metrics.metric("test")
        assert_is_instance(metric, metrics.simple_metrics.Gauge)

    def test_handle_metric_update_missing_value(self):

        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_update(req(dict()), "test")
        assert_equal(exc.exception.description, "metric value not provided")

    @raises(werkzeug.exceptions.NotFound)
    def test_handle_metric_update_missing_metric(self):
        wsgi.handle_metric_update(req(dict(value=1)), "test")

    def test_handle_metric_update(self):
        metric = metrics.new_gauge("test")

        res = wsgi.handle_metric_update(req(dict(value=1.5)), "test")
        assert_equal(res, "")

        assert_equal(metric.get(), 1.5)

