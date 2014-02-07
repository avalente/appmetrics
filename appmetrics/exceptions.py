##  Module exceptions.py
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
Exceptions module - export all the AppMetrics exceptions classes
"""


class AppMetricsError(Exception):
    """Base exception class"""
    pass


class StatisticsError(AppMetricsError, ValueError):
    """Statistic functions error"""
    pass


class DuplicateMetricError(AppMetricsError):
    """Raised if you are trying to create a metric with an already existing name"""
    pass


class InvalidMetricError(AppMetricsError, KeyError):
    """Raised if you are trying to use a metric that has not been registered"""
    pass

