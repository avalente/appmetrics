import json
import io

import mock
from nose.tools import (
    assert_equal, assert_false, assert_is_instance, raises, assert_raises,
    assert_regexp_matches)
import werkzeug, werkzeug.test

from .. import wsgi, metrics, py3comp


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
        ("/_app-metrics", 'GET', werkzeug.exceptions.NotFound),
        ("/_app-metrics/metrics", 'GET', wsgi.handle_metrics_list),
        ("/_app-metrics/metrics", 'POST', werkzeug.exceptions.MethodNotAllowed),
        ("/_app-metrics/metrics/test", 'GET', wsgi.handle_metric_show),
        ("/_app-metrics/metrics/test", 'PUT', wsgi.handle_metric_new),
        ("/_app-metrics/metrics/test", 'POST', wsgi.handle_metric_update),
        ("/_app-metrics/metrics/test", 'DELETE', wsgi.handle_metric_delete),
        ("/_app-metrics/metrics/test", 'OPTIONS', werkzeug.exceptions.MethodNotAllowed),
        ("/_app-metrics/metrics/test/sub", 'GET', werkzeug.routing.NotFound),
    ]

    mw = wsgi.AppMetricsMiddleware(None)

    for url, method, expected in tests:
        yield lambda url, method: check_dispatching(mw, url, method, expected), url, method


def test_dispatching_root():
    tests = [
        ("/metrics", 'GET', wsgi.handle_metrics_list),
        ("/metrics", 'POST', werkzeug.exceptions.MethodNotAllowed),
        ("/metrics/test", 'GET', wsgi.handle_metric_show),
        ("/metrics/test", 'PUT', wsgi.handle_metric_new),
        ("/metrics/test", 'POST', wsgi.handle_metric_update),
        ("/metrics/test", 'DELETE', wsgi.handle_metric_delete),
        ("/metrics/test", 'OPTIONS', werkzeug.exceptions.MethodNotAllowed),
        ("/metrics/test/sub", 'GET', werkzeug.routing.NotFound),
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

    def test_call_with_invalid_status(self):
        self.handler.side_effect = ValueError()

        self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='GET'), self.start_response)

        assert_equal(
            self.start_response.call_args_list,
            [mock.call("500 INTERNAL SERVER ERROR", mock.ANY)]
        )

    def test_call_with_error_implicit(self):
        self.handler.side_effect = werkzeug.exceptions.BadRequest()

        body = self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps(werkzeug.exceptions.BadRequest.description)
        assert_equal(b"".join(body), expected_body.encode('utf8'))

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

        body = self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("bad request received")

        assert_equal(b"".join(body), expected_body.encode('utf8'))

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(expected_body)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("400 BAD REQUEST", expected_headers)]
        )

    def test_call_with_invalid_method(self):
        self.handler.side_effect = werkzeug.exceptions.BadRequest()

        body = self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='POST'), self.start_response)

        expected_body = json.dumps(werkzeug.exceptions.MethodNotAllowed.description)
        assert_equal(b"".join(body), expected_body.encode('utf8'))

        assert_equal(
            self.start_response.call_args_list,
            [mock.call("405 METHOD NOT ALLOWED", mock.ANY)]
        )

        headers = dict(self.start_response.call_args_list[0][0][1])
        assert_equal(headers['Content-Type'], "application/json")
        assert_equal(headers['Content-Length'], str(len(expected_body)))
        allow = {x.strip() for x in headers['Allow'].split(",")}
        assert_equal(allow, {"HEAD", "GET"})


    def test_call_ok(self):
        self.handler.return_value = json.dumps("results")

        body = self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(self.handler.return_value)))
        ]
        assert_equal(
            self.start_response.call_args_list,
            [mock.call("200 OK", expected_headers)]
        )

        expected = json.dumps("results")

        assert_equal(b"".join(body), expected.encode('utf8'))


    def test_call_with_unicode(self):
        if py3comp.PY3:
            self.handler.return_value = json.dumps("results")
        else:
            self.handler.return_value = json.dumps("results").decode('utf8')

        body = self.mw(env("/_app-metrics/metrics", REQUEST_METHOD='GET'), self.start_response)

        expected_body = json.dumps("results")
        assert_equal(b"".join(body), expected_body.encode('utf8'))

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

        self.original_tags = metrics.TAGS
        metrics.TAGS.clear()

    def tearDown(self):
        metrics.REGISTRY.clear()
        metrics.REGISTRY.update(self.original_registry)

        metrics.TAGS.clear()
        metrics.TAGS.update(self.original_tags)

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

    @mock.patch('appmetrics.wsgi.metrics.tags')
    def test_handle_tags_list(self, tags):
        tags.return_value = dict(tag1=["test1", "test2"], tag2=["test3"])

        assert_equal(wsgi.handle_tags_list(mock.Mock()), '["tag1", "tag2"]')

    def test_handle_tag_add(self):
        metrics.REGISTRY["test1"] = mock.Mock()

        res = wsgi.handle_tag_add(mock.Mock(), "tag1", "test1")

        assert_equal(res, "")
        assert_equal(metrics.TAGS, {"tag1": {"test1"}})

    @raises(werkzeug.exceptions.BadRequest)
    def test_handle_tag_add_invalid(self):
        res = wsgi.handle_tag_add(mock.Mock(), "tag1", "test1")

        assert_equal(res, "")
        assert_equal(metrics.TAGS, {"tag1": {"test1"}})

    def test_handle_untag_not_existing(self):
        res = wsgi.handle_untag(mock.Mock(), "tag1", "test1")
        assert_equal(res, "not deleted")

    def test_handle_untag(self):
        metrics.TAGS["tag1"] = {"test1"}

        res = wsgi.handle_untag(mock.Mock(), "tag1", "test1")
        assert_equal(res, "deleted")

    @raises(werkzeug.exceptions.NotFound)
    def test_handle_tag_show_not_found(self):
        wsgi.handle_tag_show(mock.Mock(), "tag1")

    def test_handle_tag_show(self):
        metrics.new_histogram("test1")
        metrics.tag("test1", "tag1")

        res = wsgi.handle_tag_show(mock.Mock(), "tag1")
        assert_equal(res, '["test1"]')

    def test_handle_tag_show_no_expand(self):
        metrics.new_histogram("test1")
        metrics.tag("test1", "tag1")

        res = wsgi.handle_tag_show(mock.Mock(args={"expand": 'false'}), "tag1")
        assert_equal(res, '["test1"]')

    @mock.patch('appmetrics.metrics.metrics_by_tag')
    def test_handle_tag_show_no_expand(self, mbt):
        mbt.return_value = "this is a test"
        metrics.new_histogram("test1")
        metrics.tag("test1", "tag1")

        res = wsgi.handle_tag_show(mock.Mock(args={"expand": 'true'}), "tag1")
        assert_equal(res, '"this is a test"')

    @raises(werkzeug.exceptions.UnsupportedMediaType)
    def test_get_body_no_content_type(self):
        request = werkzeug.wrappers.Request(dict(CONTENT_LENGTH=10))

        wsgi.get_body(request)

    @raises(werkzeug.exceptions.UnsupportedMediaType)
    def test_get_body_bad_content_type(self):
        request = werkzeug.wrappers.Request(dict(CONTENT_LENGTH=10, CONTENT_TYPE='text/html'))

        wsgi.get_body(request)

    def test_get_body_bad_content(self):
        env = {'CONTENT_LENGTH': 4, 'CONTENT_TYPE': "application/json", 'wsgi.input': io.StringIO(u"test wrong")}
        request = werkzeug.wrappers.Request(env)

        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.get_body(request)
        assert_equal(exc.exception.description, "invalid json")

    def test_get_body(self):
        env = {'CONTENT_LENGTH': 6, 'CONTENT_TYPE': "application/json", 'wsgi.input': io.StringIO(u'"test" with garbage')}
        request = werkzeug.wrappers.Request(env)

        assert_equal(wsgi.get_body(request), 'test')

    def test_handle_metric_new_missing_type(self):
        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_new(req(dict()), "test")
        assert_equal(exc.exception.description, "metric type not provided")

    def test_handle_metric_new_invalid_type(self):
        with assert_raises(werkzeug.exceptions.BadRequest) as exc:
            wsgi.handle_metric_new(req(dict(type="xxx")), "test")
        assert_regexp_matches(exc.exception.description, "invalid metric type: .*'xxx'")

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

        assert_equal(metric.get(), dict(kind="gauge", value=1.5))

