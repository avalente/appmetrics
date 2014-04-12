import csv
import os
import time
import tempfile
import shutil

from nose import tools as nt
import mock

from .. import reporter as mm, metrics, py3comp


class TestReporter(object):
    def setUp(self):
        self.old_registry = mm.REGISTRY
        mm.REGISTRY.clear()

    def tearDown(self):
        mm.REGISTRY.clear()
        mm.REGISTRY.update(self.old_registry)

    @nt.raises(TypeError)
    def test_register_invalid_schedule(self):
        mm.register(lambda x: None, None)

    @nt.raises(TypeError)
    def test_register_invalid_callback(self):
        mm.register(None, [1])

    @mock.patch('appmetrics.reporter.Timer')
    def test_register(self, timer):
        callback = mock.Mock()
        schedule = mock.MagicMock()
        tag = mock.Mock()

        mm.register(callback, schedule, tag)

        nt.assert_equal(len(mm.REGISTRY), 1)
        nt.assert_equal(list(mm.REGISTRY.values())[0], timer.return_value)
        nt.assert_equal(
            timer.call_args_list,
            [mock.call(schedule, callback, tag)])
        nt.assert_equal(
            timer.return_value.start.call_args_list,
            [mock.call()])

    @mock.patch('appmetrics.reporter.Timer')
    def test_register_with_default_tag(self, timer):
        callback = mock.Mock()
        schedule = mock.MagicMock()

        mm.register(callback, schedule)

        nt.assert_equal(len(mm.REGISTRY), 1)
        nt.assert_equal(list(mm.REGISTRY.values())[0], timer.return_value)
        nt.assert_equal(
            timer.call_args_list,
            [mock.call(schedule, callback, None)])
        nt.assert_equal(
            timer.return_value.start.call_args_list,
            [mock.call()])

    def test_get(self):
        mm.REGISTRY = {'m1': mock.Mock(), 'm2': mock.Mock()}
        nt.assert_equal(mm.get('m2'), mm.REGISTRY['m2'])

    def test_get_not_found(self):
        mm.REGISTRY = {'m1': mock.Mock(), 'm2': mock.Mock()}
        nt.assert_is_none(mm.get('m3'))

    def test_remove(self):
        m1 = mock.Mock()
        mm.REGISTRY = {'m1': m1, 'm2': mock.Mock()}

        nt.assert_is(mm.remove('m1'), m1)

        nt.assert_not_in('m1', mm.REGISTRY)
        nt.assert_equal(
            m1.cancel.call_args_list,
            [mock.call()])

    def test_remove_not_found(self):
        m1 = mock.Mock()
        m2 = mock.Mock()

        mm.REGISTRY = {'m1': m1, 'm2': m2}

        nt.assert_is_none(mm.remove('m3'))

        nt.assert_equal(mm.REGISTRY, dict(m1=m1, m2=m2))

    def test_fixed_interval_scheduler(self):
        now = time.time()
        sched = mm.fixed_interval_scheduler(10)

        nt.assert_almost_equal(next(sched), now+10, 0)
        nt.assert_almost_equal(next(sched), now+20, 0)
        nt.assert_almost_equal(next(sched), now+30, 0)

    def test_cleanup(self):
        m1 = mock.Mock()
        m2 = mock.Mock()

        mm.REGISTRY = {'m1': m1, 'm2': m2}

        mm.cleanup()

        nt.assert_equal(
            m1.cancel.call_args_list,
            [mock.call()])

        nt.assert_equal(
            m2.cancel.call_args_list,
            [mock.call()])


class TimeMachine(object):
    """
    Helper class to "emulate" the time
    """
    def __init__(self):
        self.current_time = 0
        self.sleeps = []

    def time(self):
        self.current_time += 1
        return self.current_time - 1

    def sleep(self, how_much):
        self.current_time += how_much
        self.sleeps.append(how_much)


class TestTimer(object):
    def setUp(self):
        self.time_patch = mock.patch('appmetrics.reporter.time', TimeMachine())
        self.time = self.time_patch.start()

        self.get_metrics_patch = mock.patch('appmetrics.reporter.get_metrics')
        self.get_metrics = self.get_metrics_patch.start()

        self.callback = mock.Mock()

        self.tag = "test"

    def tearDown(self):
        self.time_patch.stop()
        self.get_metrics_patch.stop()

    def test_finite_scheduler(self):
        def scheduler():
            yield 3
            yield 5
            yield 8

        tt = mm.Timer(scheduler(), self.callback, self.tag)
        tt.start()

        tt.join()

        nt.assert_false(tt.is_running)

        nt.assert_equal(
            self.callback.call_args_list,
            [
                mock.call(self.get_metrics.return_value),
                mock.call(self.get_metrics.return_value),
                mock.call(self.get_metrics.return_value),
            ]
        )

        nt.assert_equal(self.time.current_time, 10)
        nt.assert_equal(self.time.sleeps, [3, 1, 2])

    def test_infinite_scheduler(self):
        tt = mm.Timer(mm.fixed_interval_scheduler(10), self.callback, self.tag)

        # trick: when the time is >= 1000 call tt.cancel(), else it would run forever
        self.callback.side_effect = lambda x: None if self.time.current_time < 1000 else tt.cancel()

        tt.start()

        tt.join()

        nt.assert_false(tt.is_running)
        # one run every 10 seconds, for 1000 seconds total
        nt.assert_equal(self.callback.call_count, 1000/10)

        nt.assert_equal(self.time.sleeps, [11, 8] + [9]*98)

    def test_no_metrics(self):
        self.get_metrics.return_value = {}

        def scheduler():
            yield 3
            yield 5
            yield 8

        tt = mm.Timer(scheduler(), self.callback, self.tag)
        tt.start()

        tt.join()

        nt.assert_false(tt.is_running)

        nt.assert_equal(self.callback.call_count, 0)
        nt.assert_equal(self.time.sleeps, [3, 1, 2])


class TestGetMetrics(object):
    def setUp(self):
        self.original_registy = metrics.REGISTRY.copy()
        self.original_tags = metrics.TAGS.copy()

        self.m1, self.m2, self.m3 = (mock.Mock(), mock.Mock(), mock.Mock())

        metrics.REGISTRY = dict(m1=self.m1, m2=self.m2, m3=self.m3)
        metrics.TAGS = dict(tag={'m1', 'm3'})

    def tearDown(self):
        metrics.REGISTRY.clear()
        metrics.REGISTRY.update(self.original_registy)

        metrics.TAGS.clear()
        metrics.TAGS.update(self.original_tags)

    def test_with_none(self):
        res = mm.get_metrics(None)
        expected = dict(m1=self.m1.get(), m2=self.m2.get(), m3=self.m3.get())
        nt.assert_equal(res, expected)

    def test_with_tag(self):
        res = mm.get_metrics("tag")
        expected = dict(m1=self.m1.get(), m3=self.m3.get())
        nt.assert_equal(res, expected)

    def test_with_not_existent_tag(self):
        res = mm.get_metrics("xxx")
        nt.assert_equal(res, {})


class TestCSVReporter(object):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        metrics.new_histogram("h1")
        metrics.new_histogram("h2")
        metrics.new_meter("m1")
        metrics.new_meter("m2")
        metrics.new_gauge("g1")

        self.reporter = mm.CSVReporter(self.tmpdir)

        self.data = dict(
            h1=metrics.get("h1"),
            h2=metrics.get("h2"),
            m1=metrics.get("m1"),
            m2=metrics.get("m2"),
            g1=metrics.get("g1"),
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        for name in ("h1", "h2", "m1", "m2", "g1"):
            metrics.delete_metric(name)

    def check_file(self, file_name, header, expected_data):
        with open(os.path.join(self.tmpdir, file_name), "r") as ff:
            reader = csv.reader(ff)
            data = list(reader)
            nt.assert_equal(data[0], list(header))
            nt.assert_equal(data[1:], expected_data)

    def histogram_data(self, time):
        return [time, "0", "0", "0"] + ["0.0"] * (len(mm.CSVReporter.histogram_header) - 4)

    def meter_data(self, time):
        return [time, "0", "0.0", "0.0", "0.0", "0.0", "0.0"]

    @mock.patch('appmetrics.reporter.time.time', mock.Mock(return_value=1234.5))
    def test_report_first(self):
        self.reporter(self.data)

        expected_files = ["h1_histogram.csv", "h2_histogram.csv", "m1_meter.csv", "m2_meter.csv"]

        py3comp.assert_items_equal(os.listdir(self.tmpdir), expected_files)

        hd = self.histogram_data("1234.5")
        md = self.meter_data("1234.5")

        self.check_file("h1_histogram.csv", mm.CSVReporter.histogram_header, [hd])
        self.check_file("h2_histogram.csv", mm.CSVReporter.histogram_header, [hd])

        self.check_file("m1_meter.csv", mm.CSVReporter.meter_header, [md])
        self.check_file("m2_meter.csv", mm.CSVReporter.meter_header, [md])

    @mock.patch('appmetrics.reporter.time.time')
    def test_report_multiple(self, time):
        times = [1150.2]*4 + [1140.2]*4 + [1130.2]*4
        time.side_effect = times.pop

        self.reporter(self.data)
        self.reporter(self.data)
        self.reporter(self.data)

        expected_files = ["h1_histogram.csv", "h2_histogram.csv", "m1_meter.csv", "m2_meter.csv"]

        py3comp.assert_items_equal(os.listdir(self.tmpdir), expected_files)

        hd = [self.histogram_data("1130.2"), self.histogram_data("1140.2"), self.histogram_data("1150.2")]
        md = [self.meter_data("1130.2"), self.meter_data("1140.2"), self.meter_data("1150.2")]

        self.check_file("h1_histogram.csv", mm.CSVReporter.histogram_header, hd)
        self.check_file("h2_histogram.csv", mm.CSVReporter.histogram_header, hd)

        self.check_file("m1_meter.csv", mm.CSVReporter.meter_header, md)
        self.check_file("m2_meter.csv", mm.CSVReporter.meter_header, md)
