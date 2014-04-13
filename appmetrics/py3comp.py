##  Module py3comp.py
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
Python 3 compatibility
"""

import sys
import json

PY3 = sys.version_info[0] == 3

if PY3:
    xrange = range

    def iteritems(d, **kw):
        return d.items(**kw)

    __builtin_zip = zip

    zip = lambda *args: list(__builtin_zip(*args))
else:
    xrange = xrange

    def iteritems(d, **kw):
        return d.iteritems(**kw)

    zip = zip


def assert_items_equal(*args):
    from nose import tools as nt

    if hasattr(nt, 'assert_items_equal'):
        return nt.assert_items_equal(*args)
    else:
        return nt.assert_equal(set(args[0]), set(args[1]))


def json_load(stream, charset):
    # thanks very much, python 3...
    if PY3:
        raw_data = stream.read()
        if isinstance(raw_data, str):
            return json.loads(raw_data)
        else:
            return json.loads(raw_data.decode(charset))
    else:
        return json.load(stream)

