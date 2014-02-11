import json
from cStringIO import StringIO

import mock
from nose.tools import assert_equal, assert_false, assert_is_instance

from .. import wsgi, metrics


def env(path, **kwargs):
    data = dict(PATH_INFO=path)
    data.update(kwargs)
    return data


class TestAppMetricsMiddleware(object):
    def setUp(self):
        self.app = mock.Mock()
        self.start_response = mock.Mock()

        self.mw = wsgi.AppMetricsMiddleware(self.app)


    def test_match(self):
        assert_equal(self.mw.match("/_app-metrics"), "")
        assert_equal(self.mw.match("/_app-metrics/test"), "/test")
        assert_equal(self.mw.match("/_app-metrics_test"), None)
        assert_equal(self.mw.match("/test"), None)
        assert_equal(self.mw.match("/_app-metrics/"), "/")

    def test_call_not_matching(self):
        res = self.mw(env("/"), self.start_response)
        assert_equal(res, self.app.return_value)
        assert_false(self.start_response.called)
        assert_equal(
            self.app.call_args_list,
            [mock.call(env("/"), self.start_response)])

    @mock.patch('appmetrics.wsgi.AppMetricsHandler')
    def test_call_with_invalid_status(self, handler):
        handler().handle.return_value = (302, "")

        self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        assert_equal(
            self.start_response.call_args_list,
            [mock.call("500 Internal Server Error", mock.ANY)]
        )

    @mock.patch('appmetrics.wsgi.AppMetricsHandler')
    def test_call_with_error_implicit(self, handler):
        handler().handle.return_value = (400, None)

        body = self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = self.mw.error_body(400)
        assert_equal(body, [expected_body])

        expected_headers = [
            ('Content-Type', 'text/html'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("400 Bad Request", expected_headers)]
        )

    @mock.patch('appmetrics.wsgi.AppMetricsHandler')
    def test_call_with_error_explicit(self, handler):
        handler().handle.return_value = (400, "bad request received")

        body = self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("bad request received")
        assert_equal(body, [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("400 Bad Request", expected_headers)]
        )

    @mock.patch('appmetrics.wsgi.AppMetricsHandler')
    def test_call_ok(self, handler):
        handler().handle.return_value = (200, str(json.dumps("results")))

        body = self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("results")
        assert_equal(body, [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("200 OK", expected_headers)]
        )

    @mock.patch('appmetrics.wsgi.AppMetricsHandler')
    def test_call_with_unicode(self, handler):
        handler().handle.return_value = (200, unicode(json.dumps("results")))

        body = self.mw(env("/_app-metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("results")
        assert_equal(body, [expected_body])

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("200 OK", expected_headers)]
        )

class TestAppMetricsHandlerList(object):
    def test_with_wrong_method(self):
        hh = wsgi.AppMetricsHandler(None)

        assert_equal(hh.handle("POST", ""), (405, ""))

    @mock.patch('appmetrics.wsgi.metrics.metrics')
    def test_good(self, metrics):
        metrics.return_value = ["test1", "test2"]

        hh = wsgi.AppMetricsHandler(None)

        assert_equal(hh.handle("GET", ""), (200, '["test1", "test2"]'))

class TestAppMetricsHandlerMetric(object):
    def setUp(self):
        self.original_registry = metrics.REGISTRY
        metrics.REGISTRY.clear()

    def tearDown(self):
        metrics.REGISTRY.update(self.original_registry)

    @mock.patch('appmetrics.wsgi.metrics.metric')
    def test_GET(self, metric):
        metric().get.return_value = "this is a test"

        hh = wsgi.AppMetricsHandler(None)

        res = hh.handle("GET", "test")

        expected = 200, '"this is a test"'

        assert_equal(res, expected)

    @mock.patch('appmetrics.wsgi.metrics.metric')
    def test_GET_not_found(self, metric):
        metric.side_effect = KeyError("key")

        hh = wsgi.AppMetricsHandler(None)

        res = hh.handle("GET", "/test")

        expected = 404, "No such metric: 'test'"

        assert_equal(res, expected)

    def test_DELETE(self):
        with mock.patch.dict('appmetrics.metrics.REGISTRY', dict(test=mock.Mock())):
            hh = wsgi.AppMetricsHandler(None)

            res = hh.handle("DELETE", "/test")

            assert_equal(res, (200, "deleted"))
            assert_equal(metrics.REGISTRY, dict())

    def test_DELETE_not_found(self):
        with mock.patch.dict('appmetrics.metrics.REGISTRY', dict(none="test")):
            hh = wsgi.AppMetricsHandler(None)

            res = hh.handle("DELETE", "/test")

            assert_equal(res, (200, "not deleted"))
            assert_equal(metrics.REGISTRY, dict(none="test"))

    def test_unsupported_method(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.handle("OPTIONS", "/test")

        assert_equal(res, (405, None))

    def test_body_extraction_no_content_length(self):
        hh = wsgi.AppMetricsHandler({})

        res = hh.handle("PUT", "/test")

        assert_equal(res, (411, None))

    def test_body_extraction_bad_content_length(self):
        hh = wsgi.AppMetricsHandler(dict(CONTENT_LENGTH="xxx"))

        res = hh.handle("PUT", "/test")

        assert_equal(res, (400, None))

    def test_body_extraction_no_content_type(self):
        hh = wsgi.AppMetricsHandler(dict(CONTENT_LENGTH=10))

        res = hh.handle("PUT", "/test")

        assert_equal(res, (415, None))

    def test_body_extraction_bad_content_type(self):
        hh = wsgi.AppMetricsHandler(dict(CONTENT_LENGTH=10, CONTENT_TYPE="text/html"))

        res = hh.handle("PUT", "/test")

        assert_equal(res, (415, None))

    def test_body_bad_content(self):
        env = dict(CONTENT_LENGTH=4, CONTENT_TYPE="application/json")
        env['wsgi.input'] = StringIO("test wrong")
        hh = wsgi.AppMetricsHandler(env)

        res = hh.handle("PUT", "/test")

        assert_equal(res, (400, "invalid json"))

    def test_dispatch_PUT_with_body(self):
        env = dict(CONTENT_LENGTH=6, CONTENT_TYPE="application/json")
        env['wsgi.input'] = StringIO('"test" with garbage')
        hh = wsgi.AppMetricsHandler(env)
        hh.add_value = mock.Mock()
        hh.add_metric = mock.MagicMock(return_value=(mock.Mock(), mock.Mock()))

        res = hh.handle("PUT", "/metric")

        assert_equal(res, hh.add_metric.return_value)
        assert_equal(
            hh.add_metric.call_args_list,
            [mock.call("metric", "test")]
        )
        assert_false(hh.add_value.called)

    def test_dispatch_POST_with_body(self):
        env = dict(CONTENT_LENGTH=6, CONTENT_TYPE="application/json")
        env['wsgi.input'] = StringIO('"test" with garbage')
        hh = wsgi.AppMetricsHandler(env)
        hh.add_value = mock.MagicMock(return_value=(mock.Mock(), mock.Mock()))
        hh.add_metric = mock.Mock()

        res = hh.handle("POST", "/metric")

        assert_equal(res, hh.add_value.return_value)
        assert_equal(
            hh.add_value.call_args_list,
            [mock.call("metric", "test")]
        )
        assert_false(hh.add_metric.called)

    def test_add_metric_missing_type(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_metric("test", dict())
        assert_equal(res, (400, "metric type not provided"))

    def test_add_metric_invalid_type(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_metric("test", dict(type="xxx"))
        assert_equal(res, (400, "invalid metric type: 'xxx'"))

    def test_add_metric_app_error(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_metric("test", dict(type="gauge"))
        res = hh.add_metric("test", dict(type="gauge"))
        assert_equal(res, (400, "can't create metric gauge('test'): Metric test already exists of type Gauge"))

    def test_add_metric_generic_error(self):
        new_gauge = mock.Mock(side_effect=ValueError("an error"))

        with mock.patch.dict('appmetrics.wsgi.metrics.METRIC_TYPES', gauge=new_gauge):
            hh = wsgi.AppMetricsHandler(None)

            res = hh.add_metric("test", dict(type="gauge"))
            assert_equal(res, (400, "can't create metric gauge('test')"))

    def test_add_metric(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_metric("test", dict(type="gauge"))
        assert_equal(res, (200, ""))

        metric = metrics.metric("test")
        assert_is_instance(metric, metrics.simple_metrics.Gauge)

    def test_add_value_missing_value(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_value("test", dict())
        assert_equal(res, (400, "metric value not provided"))

    def test_add_value_missing_metric(self):
        hh = wsgi.AppMetricsHandler(None)

        res = hh.add_value("test", dict(value=1))
        assert_equal(res, (404, None))

    def test_add_value(self):
        hh = wsgi.AppMetricsHandler(None)

        metric = metrics.new_gauge("test")
        res = hh.add_value("test", dict(value=1.5))
        assert_equal(res, (200, ""))

        assert_equal(metric.get(), 1.5)
