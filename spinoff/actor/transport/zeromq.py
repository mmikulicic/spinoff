import pickle

from txzmq.connection import ZmqEndpoint
from txzmq.req_rep import ZmqDealerConnection, ZmqRouterConnection, ZmqRequestConnection, ZmqReplyConnection

from spinoff.actor.actor import Actor


class ZmqProxyBase(Actor):

    CONNECTION_CLASS = None
    DEFAULT_ENDPOINT_TYPE = 'connect'

    def __init__(self, factory, endpoint=None, identity=None):
        super(ZmqProxyBase, self).__init__()
        self._identity = identity
        self._endpoints = []
        self._conn = self.CONNECTION_CLASS(factory, identity=identity)
        self._conn.gotMessage = self._zmq_msg_received

        if endpoint:
            self.add_endpoints([endpoint])

    def _zmq_msg_received(self, message):
        message = pickle.loads(message[0])
        self.parent.send(message)

    def run(self):
        while True:
            self._conn.sendMsg(pickle.dumps((yield self.get())))

    def add_endpoints(self, endpoints):
        endpoints = [
            (e if isinstance(e, ZmqEndpoint)
             else (ZmqEndpoint(*e) if isinstance(e, tuple)
                   else ZmqEndpoint(self.DEFAULT_ENDPOINT_TYPE, e)))
            for e in endpoints
            ]
        self._endpoints.extend(endpoints)
        self._conn.addEndpoints(endpoints)

    @property
    def identity(self):
        return self._identity

    def __repr__(self):
        endpoints_repr = ';'.join('%s=>%s' % (endpoint.type, endpoint.address)
                                  for endpoint in self._endpoints)
        return '<%s%s%s>' % (type(self),
                             ' ' + self._identity if self._identity else '',
                             ' ' + endpoints_repr if endpoints_repr else '')

    def stop(self):
        self._conn.shutdown()


class ZmqRouter(ZmqProxyBase):
    CONNECTION_CLASS = staticmethod(ZmqRouterConnection)
    DEFAULT_ENDPOINT_TYPE = 'bind'

    def _zmq_msg_received(self, sender_id, message):
        message = pickle.loads(message[0])
        self.parent.send((sender_id, message))

    def run(self):
        while True:
            message = yield self.get()
            assert isinstance(message, tuple) and len(message) == 2
            recipient_id, message = message
            self._conn.sendMsg(recipient_id, pickle.dumps(message))


class ZmqDealer(ZmqProxyBase):
    CONNECTION_CLASS = staticmethod(ZmqDealerConnection)


class ZmqRep(ZmqProxyBase):
    CONNECTION_CLASS = staticmethod(ZmqReplyConnection)
    DEFAULT_ENDPOINT_TYPE = 'bind'

    def _zmq_msg_received(self, message_id, message):
        self.parent.send((message_id, pickle.loads(message)))

    def run(self):
        while True:
            message = yield self.get()
            try:
                message_id, message = message
            except ValueError:
                raise Exception("ZmqRouter requires messages of the form (request_id, response)")
            msg_data_out = pickle.dumps(message)
            self._conn.sendMsg(message_id, msg_data_out)


class ZmqReq(ZmqProxyBase):
    CONNECTION_CLASS = staticmethod(ZmqRequestConnection)

    def run(self):
        while True:
            msg_data_in = yield self._conn.sendMsg(pickle.dumps((yield self.get())))
            self.parent.send(pickle.loads(msg_data_in[0]))
