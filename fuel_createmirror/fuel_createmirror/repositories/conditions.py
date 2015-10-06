#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


def _top_down(tree, key, condition):
    """Finds first element from top to down, for that condition is true."""
    result = None
    for item in tree.item_slice(None, key, reverse=True):
        if not condition(item[0], key):
            break
        result = item
    return result


def _down_up(tree, key, condition):
    """Finds first element from top to down, for that condition is true."""
    result = None
    for item in tree.item_slice(key, None):
        if not condition(item[0], key):
            break
        result = item
    return result


def less_than(tree, key):
    """Gets all that less than key."""
    return _top_down(tree, key, lambda x, y: x < y)


def less_or_equal(tree, key):
    """Gets all that less or equal key."""
    return _top_down(tree, key, lambda x, y: x <= y)


def greater_than(tree, key):
    """Gets all that greater than key."""
    return _down_up(tree, key, lambda x, y: x > y)


def greater_or_equal(tree, key):
    """Gets all that greater or equal key."""
    return _down_up(tree, key, lambda x, y: x >= y)


def equal(tree, key):
    """Gets first element, that less than key."""
    if key in tree:
        return key, tree[key]


def newest(tree, _):
    """Gets first element, that less than key."""
    return max(tree)
