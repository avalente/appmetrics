import logging

from nose.tools import assert_equal, assert_almost_equal, raises
import mock

from .. import meter as mm


log = logging.getLogger(__name__)


class TestEWMA(object):
    def test_compute_alpha(self):
        assert_almost_equal(mm.EWMA.compute_alpha(1, 5), 0.07995558537067671)
        assert_almost_equal(mm.EWMA.compute_alpha(5, 5), 0.01652854617838251)
        assert_almost_equal(mm.EWMA.compute_alpha(60 * 24, 5), 5.7868695912732804e-5)

    def test_update(self):
        obj = mm.EWMA(1, 5)
        obj.update(1)
        obj.update(5)

        assert_equal(obj.value, 6)

    @raises(ValueError)
    def test_update_bad_value(self):
        obj = mm.EWMA(1, 5)
        obj.update("xxx")

    def test_tick_first_time(self):
        obj = mm.EWMA(1, 5)
        obj.value = 5

        obj.tick()

        assert_equal(obj.value, 0)
        assert_almost_equal(obj.rate, 1.0)

        obj.tick()

        assert_equal(obj.value, 0)
        assert_almost_equal(obj.rate, 0.9200444146293233)

        obj.tick()

        assert_equal(obj.value, 0)
        assert_almost_equal(obj.rate, 0.8464817248906141)


class TestMeter(object):
    def setUp(self):
        self.meter = mm.Meter()
        self.started_on = self.meter.started_on

    def test_notify(self):
        self.meter.tick = mock.Mock()

        self.meter.notify(1)
        assert_equal(self.meter.count, 1)
        assert_equal(self.meter.m1.value, 1)
        assert_equal(self.meter.m5.value, 1)
        assert_equal(self.meter.m15.value, 1)
        assert_equal(self.meter.day.value, 1)

        assert_equal(self.meter.tick.call_args_list, [[]])

    def test_tick_all(self):
        self.meter.m1 = mock.Mock()
        self.meter.m5 = mock.Mock()
        self.meter.m15 = mock.Mock()
        self.meter.day = mock.Mock()

        self.meter.tick_all(3)

        assert_equal(self.meter.m1.tick.call_args_list, [[], [], []])
        assert_equal(self.meter.m5.tick.call_args_list, [[], [], []])
        assert_equal(self.meter.m15.tick.call_args_list, [[], [], []])
        assert_equal(self.meter.day.tick.call_args_list, [[], [], []])

    @mock.patch('appmetrics.meter.time')
    def test_tick(self, time_mod):
        self.meter.tick_all = mock.Mock()

        time_mod.time.return_value = self.started_on + 2.0
        self.meter.tick()

        time_mod.time.return_value = self.started_on + 8.1
        self.meter.tick()

        time_mod.time.return_value = self.started_on + 18.2
        self.meter.tick()

        assert_equal(self.meter.tick_all.call_args_list, [mock.call(1), mock.call(2)])

    def test_raw_data(self):
        self.meter.count = 5
        assert_equal(self.meter.raw_data(), 5)

    def test_get(self):
        self.meter.tick = mock.Mock()

        expected = dict(
            kind="meter",
            count=0,
            mean=0.0,
            one=0.0,
            five=0.0,
            fifteen=0.0,
            day=0.0
        )

        assert_equal(self.meter.get(), expected)
        assert_equal(self.meter.tick.call_args_list, [[]])

    @mock.patch('appmetrics.meter.time')
    def test_functional(self, time_mod):
        # almost functional test, except for the time module patch trick, needed
        # to make the time pass faster

        time_mod.time.return_value = self.started_on + 0.1
        self.check(0, 0, 0, 0, 0, 0)

        time_mod.time.return_value = self.started_on + 2.5
        self.meter.notify(1)

        time_mod.time.return_value = self.started_on + 3.0
        self.check(1, 1.0 / 3, 0, 0, 0, 0)

        time_mod.time.return_value = self.started_on + 5.1
        self.check(1, 1.0 / 5.1, 0.2, 0.2, 0.2, 0.2)

        self.meter.notify(23)

        time_mod.time.return_value = self.started_on + 60.1
        self.check(
            24, 24.0 / 60.1, 0.23981328001523144, 0.23085723900577299,
            0.2122512344327359, 0.2001387676963957)

        time_mod.time.return_value = self.started_on + (60 * 5) + 0.1
        self.check(
            24, 24.0 / 300.1, 0.004392333437481882, 0.1037308440614258,
            0.16256923530491085, 0.19958359810087625)

    def check(self, count, mean, one, five, fifteen, day):
        data = self.meter.get()

        log.info("data=%s", data)

        assert_equal(data['count'], count)
        assert_almost_equal(data['mean'], mean)
        assert_almost_equal(data['one'], one)
        assert_almost_equal(data['five'], five)
        assert_almost_equal(data['fifteen'], fifteen)
        assert_almost_equal(data['day'], day)