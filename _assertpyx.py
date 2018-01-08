# encoding=utf-8

# Copyright (c) 2015-2016, Activision Publishing, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Assertion library for python unit testing with a fluent API"""

from __future__ import division, print_function

__Author__ = 'JayveeYao@inherit_assertpy'
# https://github.com/ActivisionGameScience/assertpy
# import assertpy

import re
import os
import sys
import datetime
import numbers
import collections
import inspect
from contextlib import contextmanager

import json, traceback, types, inspect
from DictObject import DictObject

__version__ = '0.10'

if sys.version_info[0] == 3:
    str_types = (str,)
    xrange = range
    unicode = str
else:
    str_types = (basestring,)
    xrange = xrange
    unicode = unicode


### soft assertions ###
_soft_ctx = False
_soft_err = []

@contextmanager
def soft_assertions():
    global _soft_ctx
    global _soft_err

    _soft_ctx = True
    _soft_err = []

    yield

    if _soft_err:
        out = 'soft assertion failures:'
        for i,msg in enumerate(_soft_err):
            out += '\n%d. %s' % (i+1, msg)
        raise AXError(out)

    _soft_err = []
    _soft_ctx = False

def _ax_errDetail(errObj):
    return '%s\n%s' % (errObj, traceback.format_exc())

class Utils(object):
    class Symbol(object):
        """ like js's Symbol """
        def __init__(self, name=None):
            self.name = name or str(self)
        def __str__(self):
            return str(self.name)
        def __repr__(self):
            return "%s #%s" % (object.__repr__(self), self.name)
    @staticmethod
    def isSpecialAttr(attr=''):
        return bool(attr[:2]+attr[-2:]=='____')
    @staticmethod
    def isinstanceT(o, cls):
        if hasattr(cls, '__IsinstanceT__'):
            return cls.__IsinstanceT__(o)
        else:
            return isinstance(o, cls)
    @staticmethod
    def isSubCls(itype, subClsOf=types.TypeType):
        if not issubclass(type(itype), types.TypeType): # first need isa cls
            return False
        return True if subClsOf==types.TypeType else issubclass(itype, subClsOf)
    @staticmethod
    def isFn(o):
        return hasattr(o, '__call__')
    @staticmethod
    def isJsonItem(o):
        return isinstance(o, (types.NoneType, bool, numbers.Real, basestring, list, dict))
    @staticmethod
    def jsonItem(o, msg):
        if not Utils.isJsonItem(o):
            raise Exception('%s: type(obj)=%s must isa _jsonItemType' % (msg, type(o)))
        return o
    @staticmethod
    def stackUpFind(findFn):
        """  exam: stackUpFind(lambda i: i[0].f_locals.get('kw', {}).get('__Symbol__')) """
        stacks = inspect.stack()
        for i in range(len(stacks)):
            find = findFn(stacks[i])
            if find:
                return [find]
        return []
    @staticmethod
    def stackUpFind__Name__():
        upFind = Utils.stackUpFind(Utils._help_KwName_stackUpFind)
        return upFind[0] if upFind else None
    @staticmethod
    def KwName(func, *extChkFns):
        def wrapper(*args, **kw):
            fnName = func.__name__
            __Name__ = Utils.stackUpFind__Name__()
            if not __Name__:
                kw['__Name__'] = Utils.Symbol(fnName)
            else:
                kw['__Name__'] = Utils.Symbol('{}-{}'.format(__Name__, fnName))
            if extChkFns:
                for extChkFn in extChkFns:
                    extChkFn(kw)
            return func(*args, **kw)
        return wrapper
    @staticmethod
    def KwNameGet(kw):
        return str(kw['__Name__'])
    
    @staticmethod
    def _help_KwName_stackUpFind(istack):
        kw = istack[0].f_locals.get('kw', {})
        if kw.has_key('__Name__') and isinstance(kw['__Name__'], Utils.Symbol):
            return kw['__Name__']
        return None

### factory methods ###
def assert_that(val, description=''):
    """Factory method for the assertion builder with value to be tested and optional description."""
    global _soft_ctx
    if _soft_ctx:
        return AXBuild(val, description, 'soft')
    return AXBuild(val, description)

def assert_warn(val, description=''):
    """Factory method for the assertion builder with value to be tested, optional description, and
       just warn on assertion failures instead of raisings exceptions."""
    return AXBuild(val, description, 'warn')

def contents_of(f, encoding='utf-8'):
    """Helper to read the contents of the given file or path into a string with the given encoding.
    Encoding defaults to 'utf-8', other useful encodings are 'ascii' and 'latin-1'."""

    try:
        contents = f.read()
    except AttributeError:
        try:
            with open(f, 'r') as fp:
                contents = fp.read()
        except TypeError:
            raise AXOtherError('val must be file or path, but was type <%s>' % type(f).__name__)
        except OSError:
            if not isinstance(f, str_types):
                raise AXOtherError('val must be file or path, but was type <%s>' % type(f).__name__)
            raise

    if sys.version_info[0] == 3 and type(contents) is bytes:
        # in PY3 force decoding of bytes to target encoding
        return contents.decode(encoding, 'replace')
    elif sys.version_info[0] == 2 and encoding == 'ascii':
        # in PY2 force encoding back to ascii
        return contents.encode('ascii', 'replace')
    else:
        # in all other cases, try to decode to target encoding
        try:
            return contents.decode(encoding, 'replace')
        except AttributeError:
            pass
    # if all else fails, just return the contents "as is"
    return contents

def fail(msg=''):
    """Force test failure with the given message."""
    if len(msg) == 0:
        raise AXError('Fail!')
    else:
        raise AXError('Fail: %s!' % msg)

class AXConfig(object):
    Warn = False
    LogDebug = True
    _FmtArgs = None
    _AX_IfDebugFnsByStack = {}  # istack = inspect.stack()[1]
    @classmethod
    def log(cls, ax, *args, **kw):
        if ax.debug or (ax.debug==None and AXConfig.LogDebug):
            print(*args, **kw)
    @classmethod
    def addAXDebugFn(cls, name, fnByStack):
        descr = 'AXConfig.addAXDebugFn(fn):'
        AX(fnByStack, descr).doCalled(Utils.isFn).is_true()
        AX(fnByStack, descr).doCalled(str).doMethod('find', 'function <lambda>').is_equal_to(-1)
        cls._AX_IfDebugFnsByStack[name] = fnByStack
    @classmethod
    def ifAXDebug(cls, debug, istack):
        if debug:
            return True
        for fn in cls._AX_IfDebugFnsByStack.values():
            if fn(istack):
                return True
        return False

def AX(val, description=None, debug=None):
    """Factory method for the assertion builder with value to be tested, optional description, and
       just warn on assertion failures instead of raisings exceptions."""
    __Name__ = Utils.stackUpFind__Name__()
    stacks = [__i for __i in inspect.stack() if __i[1].find('\\helpers\\pydev\\') == -1]
    istack = stacks[1]  # 调用AX时的函数栈
    if AXConfig.ifAXDebug(debug, istack):
        fnFile = istack[1]
        fnCodes = list(istack[4])
        if description==None:
            matchGroups = re.match(r'.*AX\(([^\n,)]+)\).*', fnCodes[0]).groups()
            if len(matchGroups) == 1:
                description = matchGroups[0]
        description = description or re.sub(r'AX\(([^\n,)]+)\)', r'\1')  # 'AX(valCode).*' -> 'valCode'

        if fnCodes[-1].endswith('\\\n'):
            _m = inspect.getmodule(istack[0], istack[1])
            _m_dict = _m.__dict__ if _m else None
            _lines = inspect.linecache.getlines(fnFile, _m_dict)
            _line_start = istack[2] - 1
            for _i in range(1, 20 + 1):
                _line_next = _lines[_line_start + _i]
                fnCodes.append(_lines[istack[2]])
                if not _line_next.endswith('\\\n'):
                    break
        print('    -->%s: %s' % (__Name__, ''.join(fnCodes).strip()))
    assert description, 'must bool(description) is_true, but <{}>'.format(__Name__)
    warn = 'warn' if AXConfig.Warn else None
    ax = AXBuild(val, description, warn, debug=debug)  # warn
    return ax


class AXError(AssertionError):
    pass

class AXOtherError(TypeError):
    pass

class AXBuild(object):
    """Assertion builder."""

    def __init__(self, val, description='', kind=None, expected=None, debug=None, _valPath=()):
        """Construct the assertion builder."""
        self.val = val
        self._val_name = self.val.__name__ if hasattr(self.val, '__name__') else self.val
        self.description = description
        self.name = '@%s' % description.split('@')[-1]
        self.kind = kind
        self.expected = expected
        self.debug = debug    # 是否打印log的对象级局部开关，若为None则用AXConfig级全局开关
        self._logTmpCache = False   # log临时缓存(不换行打印)的开关
        self._valPath = _valPath + (self.val,)

    def described_as(self, description):
        """Describes the assertion.  On failure, the description is included in the error message."""
        self.description = str(description)
        return self

    def is_equal_to(self, other):
        """Asserts that val is equal to other."""
        if self.val != other:
            self._err('Expected %r to be equal to %r, but was not.' % (self._ax_brief_val(self.val), self._ax_brief_val(other)))
        return self

    def is_not_equal_to(self, other):
        """Asserts that val is not equal to other."""
        if self.val == other:
            self._err('Expected <%s> to be not equal to <%s>, but was.' % (self._ax_brief_val(self.val), self._ax_brief_val(other)))
        return self

    def is_same_as(self, other):
        """Asserts that the val is identical to other, via 'is' compare."""
        if self.val is not other:
            self._err('Expected <%s> to be identical to <%s>, but was not.' % (self._ax_brief_val(self.val), self._ax_brief_val(other)))
        return self

    def is_not_same_as(self, other):
        """Asserts that the val is not identical to other, via 'is' compare."""
        if self.val is other:
            self._err('Expected <%s> to be not identical to <%s>, but was.' % (self._ax_brief_val(self.val), self._ax_brief_val(other)))
        return self

    def is_true(self):
        """Asserts that val is true."""
        if not self.val:
            self._err('%s: Expected is <True>, but was not.' % self._ax_brief_val(self.val))
        return self

    def is_false(self):
        """Asserts that val is false."""
        if self.val:
            self._err('%s: Expected <False>, but was not.' % self._ax_brief_val(self.val))
        return self

    def is_none(self):
        """Asserts that val is none."""
        if self.val is not None:
            self._err('Expected <%s> to be <None>, but was not.' % self._ax_brief_val(self.val))
        return self

    def is_not_none(self):
        """Asserts that val is not none."""
        if self.val is None:
            self._err('Expected <%s> not <None>, but was.' % self._ax_brief_val(self.val))
        return self

    def is_type_of(self, some_type):
        """Asserts that val is of the given type."""
        if type(some_type) is not type and not hasattr(some_type, '__metaclass__'):
            raise AXOtherError('given arg must be a type')
        if type(self.val) is not some_type:
            if hasattr(self.val, '__name__'):
                t = self.val.__name__
            elif hasattr(self.val, '__class__'):
                t = self.val.__class__.__name__
            else:
                t = 'unknown'
            self._err('Expected <%s:%s> to be of type <%s>, but was not.' % (self._ax_brief_val(self.val), t, some_type.__name__))
        return self

    def is_instance_of(self, some_class):
        """Asserts that val is an instance of the given class."""
        try:
            if not isinstance(self.val, some_class):
                if hasattr(self.val, '__name__'):
                    t = self.val.__name__
                elif hasattr(self.val, '__class__'):
                    t = self.val.__class__.__name__
                else:
                    t = 'unknown'
                self._err('Expected <%s:%s> to be instance of class <%s>, but was not.' % (self._ax_brief_val(self.val), t, some_class.__name__))
        except TypeError:
            raise AXOtherError('given arg must be a class')
        return self

    def is_length(self, length):
        """Asserts that val is the given length."""
        if type(length) is not int:
            raise AXOtherError('given arg must be an int')
        if length < 0:
            raise AXOtherError('given arg must be a positive int')
        if len(self.val) != length:
            self._err('Expected <%s> to be of length <%d>, but was <%d>.' % (self._ax_brief_val(self.val), length, len(self.val)))
        return self

    def contains(self, *items):
        """Asserts that val contains the given item or items."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        elif len(items) == 1:
            if items[0] not in self.val:
                if type(self.val) is dict:
                    self._err('Expected <%s> to contain key <%s>, but did not.' % (self._ax_brief_val(self.val), items[0]))
                else:
                    self._err('Expected <%s> to contain item <%s>, but did not.' % (self._ax_brief_val(self.val), items[0]))
        else:
            for i in items:
                if i not in self.val:
                    if type(self.val) is dict:
                        self._err('Expected <%s> to contain keys %s, but did not contain key <%s>.' % (self._ax_brief_val(self.val), items, i))
                    else:
                        self._err('Expected <%s> to contain items %s, but did not contain <%s>.' % (self._ax_brief_val(self.val), items, i))
        return self

    def does_not_contain(self, *items):
        """Asserts that val does not contain the given item or items."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        elif len(items) == 1:
            if items[0] in self.val:
                self._err('Expected <%s> to not contain item <%s>, but did.' % (self._ax_brief_val(self.val), items[0]))
        else:
            for i in items:
                if i in self.val:
                    self._err('Expected <%s> to not contain items %s, but did contain <%s>.' % (self._ax_brief_val(self.val), items, i))
        return self

    def contains_only(self, *items):
        """Asserts that val contains only the given item or items."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        else:
            for i in self.val:
                if i not in items:
                    self._err('Expected <%s> to contain only %s, but did contain <%s>.' % (self._ax_brief_val(self.val), items, i))
        return self

    def contains_sequence(self, *items):
        """Asserts that val contains the given sequence of items in order."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        else:
            try:
                for i in xrange(len(self.val) - len(items) + 1):
                    for j in xrange(len(items)):
                        if self.val[i+j] != items[j]:
                            break
                    else:
                        return self
            except TypeError:
                raise AXOtherError('val is not iterable')
        self._err('Expected <%s> to contain sequence %s, but did not.' % (self.val, items))

    def contains_duplicates(self):
        """Asserts that val is iterable and contains duplicate items."""
        try:
            if len(self.val) != len(set(self.val)):
                return self
        except TypeError:
            raise AXOtherError('val is not iterable')
        self._err('Expected <%s> to contain duplicates, but did not.' % self.val)

    def does_not_contain_duplicates(self):
        """Asserts that val is iterable and does not contain any duplicate items."""
        try:
            if len(self.val) == len(set(self.val)):
                return self
        except TypeError:
            raise AXOtherError('val is not iterable')
        self._err('Expected <%s> to not contain duplicates, but did.' % self.val)

    def is_empty(self):
        """Asserts that val is empty."""
        if len(self.val) != 0:
            if isinstance(self.val, str_types):
                self._err('Expected <%s> to be empty string, but was not.' % self.val)
            else:
                self._err('Expected <%s> to be empty, but was not.' % self.val)
        return self

    def is_not_empty(self):
        """Asserts that val is not empty."""
        if len(self.val) == 0:
            if isinstance(self.val, str_types):
                self._err('Expected not empty string, but was empty.')
            else:
                self._err('Expected not empty, but was empty.')
        return self

    def is_in(self, *items):
        """Asserts that val is equal to one of the given items."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        else:
            for i in items:
                if self.val == i:
                    return self
        self._err('Expected <%s> to be in %s, but was not.' % (self.val, items))

    def is_not_in(self, *items):
        """Asserts that val is not equal to one of the given items."""
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        else:
            for i in items:
                if self.val == i:
                    self._err('Expected <%s> to not be in %s, but was.' % (self.val, items))
        return self

### numeric assertions ###

    COMPAREABLE_TYPES = set([datetime.datetime, datetime.timedelta, datetime.date, datetime.time])
    NON_COMPAREABLE_TYPES = set([complex])

    def _validate_compareable(self, other):
        self_type = type(self.val)
        other_type = type(other)

        if self_type in self.NON_COMPAREABLE_TYPES:
            raise AXOtherError('ordering is not defined for type <%s>' % self_type.__name__)
        if self_type in self.COMPAREABLE_TYPES:
            if other_type is not self_type:
                raise AXOtherError('given arg must be <%s>, but was <%s>' % (self_type.__name__, other_type.__name__))
            return
        if isinstance(self.val, numbers.Number):
            if not isinstance(other, numbers.Number):
                raise AXOtherError('given arg must be a number, but was <%s>' % other_type.__name__)
            return
        raise AXOtherError('ordering is not defined for type <%s>' % self_type.__name__)

    def is_zero(self):
        """Asserts that val is numeric and equal to zero."""
        if isinstance(self.val, numbers.Number) is False:
            raise AXOtherError('val is not numeric')
        return self.is_equal_to(0)

    def is_not_zero(self):
        """Asserts that val is numeric and not equal to zero."""
        if isinstance(self.val, numbers.Number) is False:
            raise AXOtherError('val is not numeric')
        return self.is_not_equal_to(0)

    def is_greater_than(self, other):
        """Asserts that val is numeric and is greater than other."""
        self._validate_compareable(other)
        if self.val <= other:
            if type(self.val) is datetime.datetime:
                self._err('Expected <%s> to be greater than <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                self._err('Expected <%s> to be greater than <%s>, but was not.' % (self.val, other))
        return self

    def is_greater_than_or_equal_to(self, other):
        """Asserts that val is numeric and is greater than or equal to other."""
        self._validate_compareable(other)
        if self.val < other:
            if type(self.val) is datetime.datetime:
                self._err('Expected <%s> to be greater than or equal to <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                self._err('Expected <%s> to be greater than or equal to <%s>, but was not.' % (self.val, other))
        return self

    def is_less_than(self, other):
        """Asserts that val is numeric and is less than other."""
        self._validate_compareable(other)
        if self.val >= other:
            if type(self.val) is datetime.datetime:
                self._err('Expected <%s> to be less than <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                self._err('Expected <%s> to be less than <%s>, but was not.' % (self.val, other))
        return self

    def is_less_than_or_equal_to(self, other):
        """Asserts that val is numeric and is less than or equal to other."""
        self._validate_compareable(other)
        if self.val > other:
            if type(self.val) is datetime.datetime:
                self._err('Expected <%s> to be less than or equal to <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                self._err('Expected <%s> to be less than or equal to <%s>, but was not.' % (self.val, other))
        return self

    def is_positive(self):
        """Asserts that val is numeric and greater than zero."""
        return self.is_greater_than(0)

    def is_negative(self):
        """Asserts that val is numeric and less than zero."""
        return self.is_less_than(0)

    def is_between(self, low, high):
        """Asserts that val is numeric and is between low and high."""
        self_type = type(self.val)
        low_type = type(low)
        high_type = type(high)

        if self_type in self.NON_COMPAREABLE_TYPES:
            raise AXOtherError('ordering is not defined for type <%s>' % self_type.__name__)
        if self_type in self.COMPAREABLE_TYPES:
            if low_type is not self_type:
                raise AXOtherError('given low arg must be <%s>, but was <%s>' % (self_type.__name__, low_type.__name__))
            if high_type is not self_type:
                raise AXOtherError('given high arg must be <%s>, but was <%s>' % (self_type.__name__, low_type.__name__))
        elif isinstance(self.val, numbers.Number):
            if isinstance(low, numbers.Number) is False:
                raise AXOtherError('given low arg must be numeric, but was <%s>' % low_type.__name__)
            if isinstance(high, numbers.Number) is False:
                raise AXOtherError('given high arg must be numeric, but was <%s>' % high_type.__name__)
        else:
            raise AXOtherError('ordering is not defined for type <%s>' % self_type.__name__)

        if low > high:
            raise AXOtherError('given low arg must be less than given high arg')
        if self.val < low or self.val > high:
            if self_type is datetime.datetime:
                self._err('Expected <%s> to be between <%s> and <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), low.strftime('%Y-%m-%d %H:%M:%S'), high.strftime('%Y-%m-%d %H:%M:%S')))
            else:
                self._err('Expected <%s> to be between <%s> and <%s>, but was not.' % (self.val, low, high))
        return self

    def is_close_to(self, other, tolerance):
        """Asserts that val is numeric and is close to other within tolerance."""
        if type(self.val) is complex or type(other) is complex or type(tolerance) is complex:
            raise AXOtherError('ordering is not defined for complex numbers')
        if isinstance(self.val, numbers.Number) is False and type(self.val) is not datetime.datetime:
            raise AXOtherError('val is not numeric or datetime')
        if type(self.val) is datetime.datetime:
            if type(other) is not datetime.datetime:
                raise AXOtherError('given arg must be datetime, but was <%s>' % type(other).__name__)
            if type(tolerance) is not datetime.timedelta:
                raise AXOtherError('given tolerance arg must be timedelta, but was <%s>' % type(tolerance).__name__)
        else:
            if isinstance(other, numbers.Number) is False:
                raise AXOtherError('given arg must be numeric')
            if isinstance(tolerance, numbers.Number) is False:
                raise AXOtherError('given tolerance arg must be numeric')
            if tolerance < 0:
                raise AXOtherError('given tolerance arg must be positive')
        if self.val < (other-tolerance) or self.val > (other+tolerance):
            if type(self.val) is datetime.datetime:
                tolerance_seconds = tolerance.days * 86400 + tolerance.seconds + tolerance.microseconds / 1000000
                h, rem = divmod(tolerance_seconds, 3600)
                m, s = divmod(rem, 60)
                self._err('Expected <%s> to be close to <%s> within tolerance <%d:%02d:%02d>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S'), h, m, s))
            else:
                self._err('Expected <%s> to be close to <%s> within tolerance <%s>, but was not.' % (self.val, other, tolerance))
        return self

### string assertions ###

    def is_equal_to_ignoring_case(self, other):
        """Asserts that val is case-insensitive equal to other."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if not isinstance(other, str_types):
            raise AXOtherError('given arg must be a string')
        if self.val.lower() != other.lower():
            self._err('Expected <%s> to be case-insensitive equal to <%s>, but was not.' % (self.val, other))
        return self

    def contains_ignoring_case(self, *items):
        """Asserts that val is string and contains the given item or items."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if len(items) == 0:
            raise AXOtherError('one or more args must be given')
        elif len(items) == 1:
            if not isinstance(items[0], str_types):
                raise AXOtherError('given arg must be a string')
            if items[0].lower() not in self.val.lower():
                self._err('Expected <%s> to case-insensitive contain item <%s>, but did not.' % (self.val, items[0]))
        else:
            for i in items:
                if not isinstance(i, str_types):
                    raise AXOtherError('given args must all be strings')
                if i.lower() not in self.val.lower():
                    self._err('Expected <%s> to case-insensitive contain items %s, but did not contain <%s>.' % (self.val, items, i))
        return self

    def starts_with(self, prefix):
        """Asserts that val is string or iterable and starts with prefix."""
        if prefix is None:
            raise AXOtherError('given prefix arg must not be none')
        if isinstance(self.val, str_types):
            if not isinstance(prefix, str_types):
                raise AXOtherError('given prefix arg must be a string')
            if len(prefix) == 0:
                raise AXOtherError('given prefix arg must not be empty')
            if not self.val.startswith(prefix):
                self._err('Expected <%s> to start with <%s>, but did not.' % (self.val, prefix))
        elif isinstance(self.val, collections.Iterable):
            if len(self.val) == 0:
                raise AXOtherError('val must not be empty')
            first = next(i for i in self.val)
            if first != prefix:
                self._err('Expected %s to start with <%s>, but did not.' % (self.val, prefix))
        else:
            raise AXOtherError('val is not a string or iterable')
        return self

    def ends_with(self, suffix):
        """Asserts that val is string or iterable and ends with suffix."""
        if suffix is None:
            raise AXOtherError('given suffix arg must not be none')
        if isinstance(self.val, str_types):
            if not isinstance(suffix, str_types):
                raise AXOtherError('given suffix arg must be a string')
            if len(suffix) == 0:
                raise AXOtherError('given suffix arg must not be empty')
            if not self.val.endswith(suffix):
                self._err('Expected <%s> to end with <%s>, but did not.' % (self.val, suffix))
        elif isinstance(self.val, collections.Iterable):
            if len(self.val) == 0:
                raise AXOtherError('val must not be empty')
            last = None
            for last in self.val:
                pass
            if last != suffix:
                self._err('Expected %s to end with <%s>, but did not.' % (self.val, suffix))
        else:
            raise AXOtherError('val is not a string or iterable')
        return self

    def matches(self, pattern):
        """Asserts that val is string and matches regex pattern."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if not isinstance(pattern, str_types):
            raise AXOtherError('given pattern arg must be a string')
        if len(pattern) == 0:
            raise AXOtherError('given pattern arg must not be empty')
        if re.search(pattern, self.val) is None:
            self._err('Expected <%s> to match pattern <%s>, but did not.' % (self.val, pattern))
        return self

    def does_not_match(self, pattern):
        """Asserts that val is string and does not match regex pattern."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if not isinstance(pattern, str_types):
            raise AXOtherError('given pattern arg must be a string')
        if len(pattern) == 0:
            raise AXOtherError('given pattern arg must not be empty')
        if re.search(pattern, self.val) is not None:
            self._err('Expected <%s> to not match pattern <%s>, but did.' % (self.val, pattern))
        return self

    def is_alpha(self):
        """Asserts that val is non-empty string and all characters are alphabetic."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if len(self.val) == 0:
            raise AXOtherError('val is empty')
        if not self.val.isalpha():
            self._err('Expected <%s> to contain only alphabetic chars, but did not.' % self.val)
        return self

    def is_digit(self):
        """Asserts that val is non-empty string and all characters are digits."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if len(self.val) == 0:
            raise AXOtherError('val is empty')
        if not self.val.isdigit():
            self._err('Expected <%s> to contain only digits, but did not.' % self.val)
        return self

    def is_lower(self):
        """Asserts that val is non-empty string and all characters are lowercase."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if len(self.val) == 0:
            raise AXOtherError('val is empty')
        if self.val != self.val.lower():
            self._err('Expected <%s> to contain only lowercase chars, but did not.' % self.val)
        return self

    def is_upper(self):
        """Asserts that val is non-empty string and all characters are uppercase."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a string')
        if len(self.val) == 0:
            raise AXOtherError('val is empty')
        if self.val != self.val.upper():
            self._err('Expected <%s> to contain only uppercase chars, but did not.' % self.val)
        return self

    def is_unicode(self):
        """Asserts that val is a unicode string."""
        if type(self.val) is not unicode:
            self._err('Expected <%s> to be unicode, but was <%s>.' % (self.val, type(self.val).__name__))
        return self

### collection assertions ###

    def is_iterable(self):
        """Asserts that val is iterable collection."""
        if not isinstance(self.val, collections.Iterable):
            self._err('Expected iterable, but was not.')
        return self

    def is_not_iterable(self):
        """Asserts that val is not iterable collection."""
        if isinstance(self.val, collections.Iterable):
            self._err('Expected not iterable, but was.')
        return self

    def is_subset_of(self, *supersets):
        """Asserts that val is iterable and a subset of the given superset or flattened superset if multiple supersets are given."""
        if not isinstance(self.val, collections.Iterable):
            raise AXOtherError('val is not iterable')
        if len(supersets) == 0:
            raise AXOtherError('one or more superset args must be given')

        if hasattr(self.val, 'keys') and callable(getattr(self.val, 'keys')) and hasattr(self.val, '__getitem__'):
            # flatten superset dicts
            superdict = {}
            for l,j in enumerate(supersets):
                self._check_dict_like(j, check_values=False, name='arg #%d' % (l+1))
                for k in j.keys():
                    superdict.update({k: j[k]})

            for i in self.val.keys():
                if i not in superdict:
                    self._err('Expected <%s> to be subset of %s, but key <%s> was missing.' % (self.val, superdict, i))
                if self.val[i] != superdict[i]:
                    self._err('Expected <%s> to be subset of %s, but key <%s> value <%s> was not equal to <%s>.' % (self.val, superdict, i, self.val[i], superdict[i]))
        else:
            # flatten supersets
            superset = set()
            for j in supersets:
                try:
                    for k in j:
                        superset.add(k)
                except Exception:
                    superset.add(j)

            for i in self.val:
                if i not in superset:
                    self._err('Expected <%s> to be subset of %s, but <%s> was missing.' % (self.val, superset, i))

        return self

### dict assertions ###

    def contains_key(self, *keys):
        """Asserts the val is a dict and contains the given key or keys.  Alias for contains()."""
        self._check_dict_like(self.val, check_values=False, check_getitem=False)
        return self.contains(*keys)

    def does_not_contain_key(self, *keys):
        """Asserts the val is a dict and does not contain the given key or keys.  Alias for does_not_contain()."""
        self._check_dict_like(self.val, check_values=False, check_getitem=False)
        return self.does_not_contain(*keys)

    def contains_value(self, *values):
        """Asserts that val is a dict and contains the given value or values."""
        self._check_dict_like(self.val, check_getitem=False)
        if len(values) == 0:
            raise AXOtherError('one or more value args must be given')
        for v in values:
            if v not in self.val.values():
                self._err('Expected <%s> to contain value <%s>, but did not.' % (self.val, v))
        return self

    def does_not_contain_value(self, *values):
        """Asserts that val is a dict and does not contain the given value or values."""
        self._check_dict_like(self.val, check_getitem=False)
        if len(values) == 0:
            raise AXOtherError('one or more value args must be given')
        elif len(values) == 1:
            if values[0] in self.val.values():
                self._err('Expected <%s> to not contain value <%s>, but did.' % (self.val, values[0]))
        else:
            for v in values:
                if v in self.val.values():
                    self._err('Expected <%s> to not contain values %s, but did contain <%s>.' % (self.val, values, v))
        return self

    def contains_entry(self, *entries):
        """Asserts that val is a dict and contains the given entry or entries."""
        self._check_dict_like(self.val, check_values=False)
        if len(entries) == 0:
            raise AXOtherError('one or more entry args must be given')
        for e in entries:
            if type(e) is not dict:
                raise AXOtherError('given entry arg must be a dict')
            if len(e) != 1:
                raise AXOtherError('given entry args must contain exactly one key-value pair')
            k = list(e.keys())[0]
            if k not in self.val:
                self._err('Expected <%s> to contain entry %s, but did not contain key <%s>.' % (self.val, e, k))
            elif self.val[k] != e[k]:
                self._err('Expected <%s> to contain entry %s, but key <%s> did not contain value <%s>.' % (self.val, e, k, e[k]))
        return self

    def does_not_contain_entry(self, *entries):
        """Asserts that val is a dict and does not contain the given entry or entries."""
        self._check_dict_like(self.val, check_values=False)
        if len(entries) == 0:
            raise AXOtherError('one or more entry args must be given')
        for e in entries:
            if type(e) is not dict:
                raise AXOtherError('given entry arg must be a dict')
            if len(e) != 1:
                raise AXOtherError('given entry args must contain exactly one key-value pair')
            k = list(e.keys())[0]
            if k in self.val and e[k] == self.val[k]:
                self._err('Expected <%s> to not contain entry %s, but did.' % (self.val, e))
        return self

### datetime assertions ###

    def is_before(self, other):
        """Asserts that val is a date and is before other date."""
        if type(self.val) is not datetime.datetime:
            raise AXOtherError('val must be datetime, but was type <%s>' % type(self.val).__name__)
        if type(other) is not datetime.datetime:
            raise AXOtherError('given arg must be datetime, but was type <%s>' % type(other).__name__)
        if self.val >= other:
            self._err('Expected <%s> to be before <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
        return self

    def is_after(self, other):
        """Asserts that val is a date and is after other date."""
        if type(self.val) is not datetime.datetime:
            raise AXOtherError('val must be datetime, but was type <%s>' % type(self.val).__name__)
        if type(other) is not datetime.datetime:
            raise AXOtherError('given arg must be datetime, but was type <%s>' % type(other).__name__)
        if self.val <= other:
            self._err('Expected <%s> to be after <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
        return self

    def is_equal_to_ignoring_milliseconds(self, other):
        if type(self.val) is not datetime.datetime:
            raise AXOtherError('val must be datetime, but was type <%s>' % type(self.val).__name__)
        if type(other) is not datetime.datetime:
            raise AXOtherError('given arg must be datetime, but was type <%s>' % type(other).__name__)
        if self.val.date() != other.date() or self.val.hour != other.hour or self.val.minute != other.minute or self.val.second != other.second:
            self._err('Expected <%s> to be equal to <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M:%S'), other.strftime('%Y-%m-%d %H:%M:%S')))
        return self

    def is_equal_to_ignoring_seconds(self, other):
        if type(self.val) is not datetime.datetime:
            raise AXOtherError('val must be datetime, but was type <%s>' % type(self.val).__name__)
        if type(other) is not datetime.datetime:
            raise AXOtherError('given arg must be datetime, but was type <%s>' % type(other).__name__)
        if self.val.date() != other.date() or self.val.hour != other.hour or self.val.minute != other.minute:
            self._err('Expected <%s> to be equal to <%s>, but was not.' % (self.val.strftime('%Y-%m-%d %H:%M'), other.strftime('%Y-%m-%d %H:%M')))
        return self

    def is_equal_to_ignoring_time(self, other):
        if type(self.val) is not datetime.datetime:
            raise AXOtherError('val must be datetime, but was type <%s>' % type(self.val).__name__)
        if type(other) is not datetime.datetime:
            raise AXOtherError('given arg must be datetime, but was type <%s>' % type(other).__name__)
        if self.val.date() != other.date():
            self._err('Expected <%s> to be equal to <%s>, but was not.' % (self.val.strftime('%Y-%m-%d'), other.strftime('%Y-%m-%d')))
        return self

### file assertions ###

    def exists(self):
        """Asserts that val is a path and that it exists."""
        if not isinstance(self.val, str_types):
            raise AXOtherError('val is not a path')
        if not os.path.exists(self.val):
            self._err('Expected <%s> to exist, but not found.' % self.val)
        return self

    def is_file(self):
        """Asserts that val is an existing path to a file."""
        self.exists()
        if not os.path.isfile(self.val):
            self._err('Expected <%s> to be a file, but was not.' % self.val)
        return self

    def is_directory(self):
        """Asserts that val is an existing path to a directory."""
        self.exists()
        if not os.path.isdir(self.val):
            self._err('Expected <%s> to be a directory, but was not.' % self.val)
        return self

    def is_named(self, filename):
        """Asserts that val is an existing path to a file and that file is named filename."""
        self.is_file()
        if not isinstance(filename, str_types):
            raise AXOtherError('given filename arg must be a path')
        val_filename = os.path.basename(os.path.abspath(self.val))
        if val_filename != filename:
            self._err('Expected filename <%s> to be equal to <%s>, but was not.' % (val_filename, filename))
        return self

    def is_child_of(self, parent):
        """Asserts that val is an existing path to a file and that file is a child of parent."""
        self.is_file()
        if not isinstance(parent, str_types):
            raise AXOtherError('given parent directory arg must be a path')
        val_abspath = os.path.abspath(self.val)
        parent_abspath = os.path.abspath(parent)
        if not val_abspath.startswith(parent_abspath):
            self._err('Expected file <%s> to be a child of <%s>, but was not.' % (val_abspath, parent_abspath))
        return self

### collection of objects assertions ###

    def extracting(self, *names):
        """Asserts that val is collection, then extracts the named properties or named zero-arg methods into a list (or list of tuples if multiple names are given)."""
        if not isinstance(self.val, collections.Iterable):
            raise AXOtherError('val is not iterable')
        if isinstance(self.val, str_types):
            raise AXOtherError('val must not be string')
        if len(names) == 0:
            raise AXOtherError('one or more name args must be given')
        extracted = []
        for i in self.val:
            items = []
            for name in names:
                if type(i) is dict:
                    if name in i:
                        items.append(i[name])
                    else:
                        raise AXOtherError('item keys %s did not contain key <%s>' % (list(i.keys()), name))
                elif hasattr(i, name):
                    attr = getattr(i, name)
                    if callable(attr):
                        try:
                            items.append(attr())
                        except TypeError:
                            raise AXOtherError('val method <%s()> exists, but is not zero-arg method' % name)
                    else:
                        items.append(attr)
                else:
                    raise AXOtherError('val does not have property or zero-arg method <%s>' % name)
            extracted.append(tuple(items) if len(items) > 1 else items[0])
        return AXBuild(extracted, self.description, self.kind)

### dynamic assertions ###
    def __getattr__(self, attr):
        """Asserts that val has attribute attr and that attribute's value is equal to other via a dynamic assertion of the form: has_<attr>()."""
        if not attr.startswith('has_'):
            raise AXOtherError('assertpy has no assertion <%s()>' % attr)

        attr_name = attr[4:]
        if not hasattr(self.val, attr_name):
            if isinstance(self.val, collections.Iterable) and hasattr(self.val, '__getitem__'):
                if attr_name not in self.val:
                    raise KeyError('val has no key <%s>' % attr_name)
            else:
                raise AXOtherError('val has no attribute <%s>' % attr_name)

        def _wrapper(*args, **kwargs):
            if len(args) != 1:
                raise AXOtherError('assertion <%s()> takes exactly 1 argument (%d given)' % (attr, len(args)))
            expected = args[0]
            try:
                val_attr = getattr(self.val, attr_name)
            except AttributeError:
                val_attr = self.val[attr_name]

            if callable(val_attr):
                try:
                    actual = val_attr()
                except TypeError:
                    raise AXOtherError('val does not have zero-arg method <%s()>' % attr_name)
            else:
                actual = val_attr

            if actual != expected:
                self._err('has_%s=%r: but expected %r' % (attr_name, actual, expected))
            return self
        return _wrapper

### expected exceptions ###

    def raises(self, ex):
        """Asserts that val is a function that when invoked raises the given error."""
        if not inspect.isfunction(self.val):
            raise AXOtherError('val must be function')
        if not issubclass(ex, BaseException):
            raise AXOtherError('given arg must be exception')
        return AXBuild(self.val, self.description, self.kind, ex, _valPath=self._valPath)

    def when_called_with(self, *some_args, **some_kwargs):
        """Asserts the val function when invoked with the given args and kwargs raises the expected exception."""
        paramsFmt = self._fmt_args_kwargs(*some_args, **some_kwargs)
        if not self.expected:
            raise AXOtherError('expected exception not set, raises() must be called first')
        try:
            self.val(*some_args, **some_kwargs)
        except BaseException as e:
            if issubclass(type(e), self.expected):
                # chain on with exception message as val
                descrNew = '%s.doCatch(%s, %s)' % (self.description, self.expected.__name__, paramsFmt)
                return AXBuild(str(e), descrNew, self.kind, _valPath=self._valPath)
            else:
                # got exception, but wrong type, so raise
                self._err('Expected <%s> to raise <%s> when called with (%s), but raised <%s>.' % (
                    self.val.__name__,
                    self.expected.__name__,
                    self._fmt_args_kwargs(*some_args, **some_kwargs),
                    type(e).__name__))

        # didn't fail as expected, so raise
        self._err('Expected <%s> to raise <%s> when called with (%s).' % (
            self.val.__name__,
            self.expected.__name__,
            self._fmt_args_kwargs(*some_args, **some_kwargs)))

### helpers ###
    def _ax_brief_val(self, val):
        str_valLast = str(val)
        max = 500
        if len(str_valLast) > max:
            if isinstance(val, dict):
                val = 'dict<.keys(%r)>' % val.keys()
            elif isinstance(val, (list, tuple, set)):
                val = 'list<.len(%s)>' % len(val)
            else:
                val = repr('%s<%s...>' % (type(val), str_valLast[:max]))
        return val
    def _err(self, msg):
        """Helper to raise an AXError, and optionally prepend custom description."""
        if len(self._valPath) >= 2:
            valLast = self._ax_brief_val(self._valPath[-2])
            msg += '\n    #_valPath[last]=%r' % valLast
        out = '[{}]: {}'.format(self.description, msg)
        if self.kind == 'warn':
            print(out)
            return self
        elif self.kind == 'soft':
            global _soft_err
            _soft_err.append(out)
            return self
        else:
            raise AXError(out)

    def _fmt_args_kwargs(self, *some_args, **some_kwargs):
        """Helper to convert the given args and kwargs into a string."""
        if some_args:
            out_args = str(some_args).lstrip('(').rstrip(',)')
        if some_kwargs:
            out_kwargs = ', '.join([str(i).lstrip('(').rstrip(')').replace(', ',': ') for i in [
                    (k,some_kwargs[k]) for k in sorted(some_kwargs.keys())]])

        if some_args and some_kwargs:
            return out_args + ', ' + out_kwargs
        elif some_args:
            return out_args
        elif some_kwargs:
            return out_kwargs
        else:
            return ''

    def _check_dict_like(self, d, check_keys=True, check_values=True, check_getitem=True, name='val'):
        if not isinstance(d, collections.Iterable):
            raise AXOtherError('%s <%s> is not dict-like: not iterable' % (name, type(d).__name__))
        if check_keys:
            if not hasattr(d, 'keys') or not callable(getattr(d, 'keys')):
                raise AXOtherError('%s <%s> is not dict-like: missing keys()' % (name, type(d).__name__))
        if check_values:
            if not hasattr(d, 'values') or not callable(getattr(d, 'values')):
                raise AXOtherError('%s <%s> is not dict-like: missing values()' % (name, type(d).__name__))
        if check_getitem:
            if not hasattr(d, '__getitem__'):
                raise AXOtherError('%s <%s> is not dict-like: missing [] accessor' % (name, type(d).__name__))

### extends ###

    def isIn(self, expect):
        if not (self.val in expect):
            self._err('Expected (%r in %r), but was not.' % (self._ax_brief_val(self.val), self._ax_brief_val(expect)))
        return self

    def isSetEq(self, expect):
        """ set(self.val) == set(expect) """
        if set(self.val) != set(expect):
            self._err('Expected set(<%r == %r>), but was not.' % (self._ax_brief_val(self.val), expect))
        return self

    def isItemsEq(self, expe, F=lambda x:x[:1]=='_', T=None, moreKeys=[], notAll=True):
        """ F<falseKeys, donnot check>
            T<trueKeys, need check, default=None is fact.keys()==expe.keys()> 
            moreKeys<not in expe> 
        """
        if not isinstance(expe, dict) and hasattr(expe, '__Json__'):  # 隐式支持  JsonT.__Json__
            expe = expe.__Json__

        if not isinstance(expe, dict):
            return self._err('expe=%r: not isinstance(expe, dict), type(expe)=%s' % (self._ax_brief_val(expe), type(expe)))
        if not isinstance(F, (list, types.FunctionType)):
            return self._err('F=%r: not isinstance(F, (list, function)), type(F)=%s' % (self._ax_brief_val(F), type(F)))
        if not (T is None or isinstance(T, list)):
            return self._err('T=%r: not isinstance(_JsonT, list), type(T)=%s' % (self._ax_brief_val(T), type(T)))
        falseKeys = F if isinstance(F, list) else [__i for __i in self.val.keys() if F(__i)]
        testKeys = sorted(set(self.val.keys()) - set(falseKeys))
        expeKeys = sorted(
            set(expe.keys()) - set(F if isinstance(F, list) else [__i for __i in expe.keys() if F(__i)])
        )
        if not notAll and testKeys != expeKeys:
            self._err('when not notAll, must: testKeys==expeKeys, but test-expe=%s expe-test=%s'
                      % (list(set(testKeys)-set(expeKeys)), list(set(expeKeys)-set(testKeys))))
        trueKeys = testKeys if T is None else T
        for k, v in self.val.items():
            if k in falseKeys or k not in trueKeys:
                continue
            if k in moreKeys:
                if not (k not in expeKeys):
                    self._err('moreKey=%r must: not in expect.keys()=%s' % (k, expeKeys))
            else:
                if not (k in expeKeys):
                    self._err('trueKey=%r must: in expect.keys()=%s' % (k, expeKeys))
                if isinstance(v, dict):
                    descrNew = '%s.%s' % (self.description, k)
                    AXBuild(v, descrNew, self.kind, expected=self.expected, debug=self.debug, _valPath=self._valPath)\
                        .isItemsEq(expe[k], F=F)
                elif getattr(v, '__Json__', None) and not hasattr(getattr(v, '__Json__'), '__call__'):
                    descrNew = '%s.%s.__Json__' % (self.description, k)
                    AXBuild(v.__Json__, descrNew, self.kind, expected=self.expected, debug=self.debug, _valPath=self._valPath).\
                        isItemsEq(expe[k], F=F)
                elif isinstance(v, list) and len(v)!=0 and isinstance(v[0], dict)\
                        and isinstance(expe[k], list) and len(expe[k])!=0 and isinstance(expe[k][0], dict):
                    for _i in range(len(v)):
                        _iv = v[_i]
                        descrNew = '%s.%s[%s]' % (self.description, k, _i)
                        AXBuild(_iv, descrNew, self.kind, expected=self.expected, debug=self.debug,
                                _valPath=self._valPath) \
                            .isItemsEq(expe[k][_i], F=F)
                else:
                    if not (v == expe[k]):
                        self._err('trueKey=%r must: test(%r) == expe(%r)' % (k, self._ax_brief_val(v), self._ax_brief_val(expe[k])))
        return self

    def doAttr(self, attr, *args):
        """ AX(obj).doAttr(attr) => AX(obj.attr) """
        try:
            sub_val = getattr(self.val, attr, *args)
            return AXBuild(sub_val, '%s.doAttr(%s, *%s)' % (self.description, attr, args), self.kind, _valPath=self._valPath)
        except BaseException as e:
            self._err('Expected <%s>.%s, but raised <%s>.' % (
                self._ax_brief_val(self.val),
                attr,
                e))

    def doProps(self):
        """ AX(obj).doProps() => AX(obj.__dict__<property>) """
        if isinstance(self.val, DictObject):
            objVarDc = self.val
        else:
            objVarDc = {i: j for i, j in self.val.__dict__.items() \
                       if i[:2] + i[-2:] != '____' and not hasattr(getattr(self.val, i), '__call__')}
        return AXBuild(objVarDc, '%s.doProps()' % self.description, self.kind, _valPath=self._valPath)

    def doAttrProps(self, attr):
        """ AX(obj).doAttrProps(attr) => AX(obj).doAttr(attr).doProps() """
        ax = self.doAttr(attr)
        return ax.doProps()

    def doCatch(self, excepted, *args, **kw):
        """ try: self.val(*args, **kw) 
            except excepted as e: return AX(e) 
        """
        if not (inspect.isfunction(self.val) or hasattr(self.val, '__call__')):
            raise AXOtherError('val must be function or has "__call__"')
        if not issubclass(excepted, BaseException):
            raise AXOtherError('given arg must be exception')
        self.expected = excepted
        return self.when_called_with(*args, **kw)

    def doCalled(self, func, *args, **kw):
        """ try: ret = func(self.val, *args, **kw); return AX(ret) """
        if not hasattr(func, '__call__'):
            raise AXOtherError('func=%r must has "__call__"' % func)

        paramsFmt = self._fmt_args_kwargs(*args, **kw)
        descrNew = '%s.doCalled(%s, %s)' % (self.description, func.__name__, paramsFmt)
        __NotAutoArg__ = False
        if kw.get('__NotAutoArg__'):
            __NotAutoArg__ = True
            kw.pop('__NotAutoArg__')
        try:
            if __NotAutoArg__:
                ret = func(*args, **kw)
            else:
                ret = func(self.val,*args, **kw)
            return AXBuild(ret, descrNew, self.kind, _valPath=self._valPath)
        except BaseException as e:
            self._err('Expected <%s> be_called %s(%s), but raised <%s>.' % (
                self._ax_brief_val(self.val),
                func.__name__,
                paramsFmt,
                e))

    def doJson(self, *args, **kw):
        return self.doCalled(json.loads, *args, **kw)

    def doMethod(self, method, *args, **kw):
        """ try: ret = self.val.method(*args, **kw); return AX(ret) """
        paramsFmt = self._fmt_args_kwargs(*args, **kw)
        if not hasattr(self.val, method):
            raise AXOtherError('%s not hasattr %r' % (self._val_name, method))
        methodObj = getattr(self.val, method)
        if not hasattr(methodObj, '__call__'):
            raise AXOtherError('%s.%s=%r not has "__call__"'
                               % (self._val_name, method, methodObj))

        try:
            methodObj = getattr(self.val, method)
            ret = methodObj(*args, **kw)
            descrNew = '%s.doMethod(%s, %s)' % (self.description, method, paramsFmt)
            return AXBuild(ret, descrNew, self.kind, _valPath=self._valPath)
        except BaseException as e:
            self._err('Expected <%s>.%s(%s), but raised <%s>.' % (
                self._ax_brief_val(self.val),
                method,
                self._fmt_args_kwargs(*args, **kw),
                e))

    def doGeti(self, item):
        """ try: ret = self.val[item]; return AX(ret) """
        return self.doMethod('__getitem__', item)
# end class

AXNone = AXBuild(None)
