# -*- coding: utf-8 -*-
"""Defines unit tests for h.streamer."""

import unittest

from collections import namedtuple
import json

import pytest
import mock
from mock import ANY
from mock import MagicMock, Mock
from mock import patch
from pyramid import security
from pyramid.testing import DummyRequest

from h import streamer
from h.streamer import WebSocket
from h.streamer import websocket


FakeMessage = namedtuple('FakeMessage', 'body')


class FakeSocket(object):
    client_id = None
    filter = None
    request = None
    terminated = None

    def __init__(self, client_id):
        self.client_id = client_id
        self.terminated = False
        self.filter = MagicMock()
        self.request = MagicMock()
        self.request.effective_principals = [security.Everyone]
        self.send = MagicMock()


def test_websocket_bad_origin(config):
    config.registry.settings.update({'origins': 'http://good'})
    config.include('h.streamer')
    req = DummyRequest(headers={'Origin': 'http://bad'})
    res = websocket(req)
    assert res.code == 403


def test_websocket_good_origin(config):
    config.registry.settings.update({'origins': 'http://good'})
    config.include('h.streamer')
    req = DummyRequest(headers={'Origin': 'http://good'})
    req.get_response = MagicMock()
    res = websocket(req)
    assert res.code != 403


def test_websocket_same_origin(config):
    config.include('h.streamer')
    # example.com is the dummy request default host URL
    req = DummyRequest(headers={'Origin': 'http://example.com'})
    req.get_response = MagicMock()
    res = websocket(req)
    assert res.code != 403


class TestWebSocket(unittest.TestCase):
    def setUp(self):
        fake_request = MagicMock()
        fake_socket = MagicMock()

        self.s = WebSocket(fake_socket)
        self.s.request = fake_request

    def test_filter_message_with_uri_gets_expanded(self):
        filter_message = json.dumps({
            'filter': {
                'actions': {},
                'match_policy': 'include_all',
                'clauses': [{
                    'field': '/uri',
                    'operator': 'equals',
                    'value': 'http://example.com',
                }],
            }
        })

        with patch('h.api.storage.expand_uri') as expand_uri:
            expand_uri.return_value = ['http://example.com',
                                       'http://example.com/alter',
                                       'http://example.com/print']
            msg = MagicMock()
            msg.data = filter_message

            self.s.received_message(msg)

            uri_filter = self.s.filter.filter['clauses'][0]
            uri_values = uri_filter['value']
            assert len(uri_values) == 3
            assert 'http://example.com' in uri_values
            assert 'http://example.com/alter' in uri_values
            assert 'http://example.com/print' in uri_values


def test_handle_annotation_event_annotation_notification_format():
    """Check the format of the returned notification in the happy case."""
    message = {
        'annotation': {'permissions': {'read': ['group:__world__']}},
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')

    assert streamer.handle_annotation_event(message, socket) == {
        'payload': [message['annotation']],
        'type': 'annotation-notification',
        'options': {'action': 'update'},
    }


def test_handle_annotation_event_none_for_sender_socket():
    """Should return None if the socket's client_id matches the message's."""
    message = {
        'annotation': {'permissions': {'read': ['group:__world__']}},
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('pigeon')

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_none_if_no_socket_filter():
    """Should return None if the socket has no filter."""
    message = {
        'annotation': {'permissions': {'read': ['group:__world__']}},
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.filter = None

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_none_if_action_is_read():
    """Should return None if the message action is 'read'."""
    message = {
        'annotation': {'permissions': {'read': ['group:__world__']}},
        'action': 'read',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_none_if_filter_does_not_match():
    """Should return None if the socket filter doesn't match the message."""
    message = {
        'annotation': {'permissions': {'read': ['group:__world__']}},
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.filter.match.return_value = False

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_none_if_annotation_nipsad():
    """Should return None if the annotation is from a NIPSA'd user."""
    message = {
        'annotation': {
            'user': 'fred',
            'nipsa': True,
            'permissions': {'read': ['group:__world__']}
        },
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_sends_nipsad_annotations_to_owners():
    """NIPSA'd users should see their own annotations."""
    message = {
        'annotation': {
            'user': 'fred',
            'nipsa': True,
            'permissions': {'read': ['group:__world__']}
        },
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.request.authenticated_userid = 'fred'

    assert streamer.handle_annotation_event(message, socket) is not None


def test_handle_annotation_event_sends_if_annotation_public():
    """
    Everyone should see annotations which are public.

    When logged-out, effective principals contains only
    `pyramid.security.Everyone`. This test ensures that the system
    principal is correctly equated with the annotation principal
    'group:__world__', ensuring that everyone (including logged-out users)
    receives all public annotations.
    """
    message = {
        'annotation': {
            'user': 'fred',
            'permissions': {'read': ['group:__world__']}
        },
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.request.effective_principals = [security.Everyone]

    assert streamer.handle_annotation_event(message, socket) is not None


def test_handle_annotation_event_none_if_not_in_group():
    """Users shouldn't see annotations in groups they aren't members of."""
    message = {
        'annotation': {
            'user': 'fred',
            'permissions': {'read': ['group:private-group']}
        },
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.request.effective_principals = ['fred']  # No 'group:private-group'.

    assert streamer.handle_annotation_event(message, socket) is None


def test_handle_annotation_event_sends_if_in_group():
    """Users should see annotations in groups they are members of."""
    message = {
        'annotation': {
            'user': 'fred',
            'permissions': {'read': ['group:private-group']}
        },
        'action': 'update',
        'src_client_id': 'pigeon'
    }
    socket = FakeSocket('giraffe')
    socket.request.effective_principals = ['fred', 'group:private-group']

    assert streamer.handle_annotation_event(message, socket) is not None


def test_handle_user_event_sends_session_change_when_joining_or_leaving_group():
    session_model = Mock()
    message = {
        'type': 'group-join',
        'userid': 'amy',
        'group': 'groupid',
        'session_model': session_model,
    }

    sock = FakeSocket('clientid')
    sock.request.authenticated_userid = 'amy'

    assert streamer.handle_user_event(message, sock) == {
        'type': 'session-change',
        'action': 'group-join',
        'model': session_model,
    }


def test_handle_user_event_none_when_socket_is_not_event_users():
    """Don't send session-change events if the event user is not the socket user."""
    message = {
        'type': 'group-join',
        'userid': 'amy',
        'group': 'groupid',
    }

    sock = FakeSocket('clientid')
    sock.request.authenticated_userid = 'bob'

    assert streamer.handle_user_event(message, sock) is None


@patch('h.streamer.WebSocket')
def test_process_message_calls_handler_once_per_socket_with_deserialized_message(websocket):
    handler = Mock()
    handler.return_value = None
    message = FakeMessage('{"foo": "bar"}')
    websocket.instances = [FakeSocket('a'), FakeSocket('b')]

    streamer.process_message(handler, Mock(), message)

    assert handler.mock_calls == [
        mock.call({'foo': 'bar'}, websocket.instances[0]),
        mock.call({'foo': 'bar'}, websocket.instances[1]),
    ]


@patch('h.streamer.WebSocket')
def test_process_message_sends_serialized_messages_down_websocket(websocket):
    handler = Mock()
    handler.return_value = {'just': 'some message'}
    message = FakeMessage('{"foo": "bar"}')
    socket = FakeSocket('a')
    websocket.instances = [socket]

    streamer.process_message(handler, Mock(), message)

    socket.send.assert_called_once_with('{"just": "some message"}')


@patch('h.streamer.WebSocket')
def test_process_message_does_not_send_messages_down_websocket_if_handler_response_is_none(websocket):
    handler = Mock()
    handler.return_value = None
    message = FakeMessage('{"foo": "bar"}')
    socket = FakeSocket('a')
    websocket.instances = [socket]

    streamer.process_message(handler, Mock(), message)

    assert socket.send.call_count == 0


@patch('h.streamer.WebSocket')
def test_process_message_does_not_send_messages_down_websocket_if_socket_terminated(websocket):
    handler = Mock()
    handler.return_value = {'just': 'some message'}
    message = FakeMessage('{"foo": "bar"}')
    socket = FakeSocket('a')
    socket.terminated = True
    websocket.instances = [socket]

    streamer.process_message(handler, Mock(), message)

    assert socket.send.call_count == 0


def test_process_queue_creates_reader_for_topic(get_reader):
    settings = {'foo': 'bar'}

    streamer.process_queue(settings, 'donkeys', lambda m, s: None)

    get_reader.assert_any_call(settings, 'donkeys', ANY)


@patch('h.streamer.process_message')
def test_process_queue_connects_reader_on_message_to_process_message(process_message, get_reader):
    settings = {'foo': 'bar'}
    handler = Mock()
    reader = get_reader.return_value

    streamer.process_queue(settings, 'donkeys', handler)
    message_handler = reader.on_message.connect.call_args[1]['receiver']
    message_handler(reader, 'message')

    process_message.assert_called_once_with(handler, reader, 'message')


def test_process_queue_starts_reader(get_reader):
    settings = {'foo': 'bar'}
    reader = get_reader.return_value

    streamer.process_queue(settings, 'donkeys', lambda m, s: None)

    reader.start.assert_called_once_with(block=True)


def test_process_queue_close_readers_explicitly_if_it_stops(get_reader):
    settings = {'foo': 'bar'}
    reader = get_reader.return_value

    streamer.process_queue(settings, 'gorillas', lambda m, s: None)

    reader.close.assert_called_once_with()


@pytest.fixture
def get_reader(request):
    patcher = patch('h.queue.get_reader')
    mock = patcher.start()
    request.addfinalizer(patcher.stop)
    return mock
