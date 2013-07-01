# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

from nova import context
from nova import exception
from nova import test


class FakeNotifier(object):
    """Acts like the nova.notifier.api module."""
    ERROR = 88

    def __init__(self):
        self.provided_publisher = None
        self.provided_event = None
        self.provided_priority = None
        self.provided_payload = None

    def notify(self, context, publisher, event, priority, payload):
        self.provided_publisher = publisher
        self.provided_event = event
        self.provided_priority = priority
        self.provided_payload = payload
        self.provided_context = context


def good_function(self, context):
    return 99


def bad_function_exception(self, context, extra, blah="a", boo="b", zoo=None):
    raise test.TestingException()


class WrapExceptionTestCase(test.TestCase):
    def test_wrap_exception_good_return(self):
        wrapped = exception.wrap_exception()
        self.assertEquals(99, wrapped(good_function)(1, 2))

    def test_wrap_exception_throws_exception(self):
        wrapped = exception.wrap_exception()
        self.assertRaises(test.TestingException,
                          wrapped(bad_function_exception), 1, 2, 3)

    def test_wrap_exception_with_notifier(self):
        notifier = FakeNotifier()
        wrapped = exception.wrap_exception(notifier, "publisher", "event",
                                           "level")
        ctxt = context.get_admin_context()
        self.assertRaises(test.TestingException,
                          wrapped(bad_function_exception), 1, ctxt, 3, zoo=3)
        self.assertEquals(notifier.provided_publisher, "publisher")
        self.assertEquals(notifier.provided_event, "event")
        self.assertEquals(notifier.provided_priority, "level")
        self.assertEquals(notifier.provided_context, ctxt)
        for key in ['exception', 'args']:
            self.assertTrue(key in notifier.provided_payload.keys())

    def test_wrap_exception_with_notifier_defaults(self):
        notifier = FakeNotifier()
        wrapped = exception.wrap_exception(notifier)
        self.assertRaises(test.TestingException,
                          wrapped(bad_function_exception), 1, 2, 3)
        self.assertEquals(notifier.provided_publisher, None)
        self.assertEquals(notifier.provided_event, "bad_function_exception")
        self.assertEquals(notifier.provided_priority, notifier.ERROR)


class NovaExceptionTestCase(test.TestCase):
    def test_default_error_msg(self):
        class FakeNovaException(exception.NovaException):
            message = "default message"

        exc = FakeNovaException()
        self.assertEquals(unicode(exc), 'default message')

    def test_error_msg(self):
        self.assertEquals(unicode(exception.NovaException('test')),
                          'test')

    def test_default_error_msg_with_kwargs(self):
        class FakeNovaException(exception.NovaException):
            message = "default message: %(code)s"

        exc = FakeNovaException(code=500)
        self.assertEquals(unicode(exc), 'default message: 500')

    def test_error_msg_exception_with_kwargs(self):
        class FakeNovaException(exception.NovaException):
            message = "default message: %(mispelled_code)s"

        exc = FakeNovaException(code=500, mispelled_code='blah')
        self.assertEquals(unicode(exc), 'default message: blah')

    def test_default_error_code(self):
        class FakeNovaException(exception.NovaException):
            code = 404

        exc = FakeNovaException()
        self.assertEquals(exc.kwargs['code'], 404)

    def test_error_code_from_kwarg(self):
        class FakeNovaException(exception.NovaException):
            code = 500

        exc = FakeNovaException(code=404)
        self.assertEquals(exc.kwargs['code'], 404)

    def test_cleanse_dict(self):
        kwargs = {'foo': 1, 'blah_pass': 2, 'zoo_password': 3, '_pass': 4}
        self.assertEquals(exception._cleanse_dict(kwargs), {'foo': 1})

        kwargs = {}
        self.assertEquals(exception._cleanse_dict(kwargs), {})

    def test_format_message_local(self):
        class FakeNovaException(exception.NovaException):
            message = "some message"

        exc = FakeNovaException()
        self.assertEquals(unicode(exc), exc.format_message())

    def test_format_message_remote(self):
        class FakeNovaException_Remote(exception.NovaException):
            message = "some message"

            def __unicode__(self):
                return u"print the whole trace"

        exc = FakeNovaException_Remote()
        self.assertEquals(unicode(exc), u"print the whole trace")
        self.assertEquals(exc.format_message(), "some message")

    def test_format_message_remote_error(self):
        class FakeNovaException_Remote(exception.NovaException):
            message = "some message %(somearg)s"

            def __unicode__(self):
                return u"print the whole trace"

        self.flags(fatal_exception_format_errors=False)
        exc = FakeNovaException_Remote(lame_arg='lame')
        self.assertEquals(exc.format_message(), "some message %(somearg)s")


class ExceptionTestCase(test.TestCase):
    @staticmethod
    def _raise_exc(exc):
        raise exc()

    def test_exceptions_raise(self):
        # NOTE(dprince): disable format errors since we are not passing kwargs
        self.flags(fatal_exception_format_errors=False)
        for name in dir(exception):
            exc = getattr(exception, name)
            if isinstance(exc, type):
                self.assertRaises(exc, self._raise_exc, exc)
