import logging

from ..api.action import Action
from ..payload import ErrorPayload
from ..payload import Payload
from ..payload import TransportPayload
from ..worker import ComponentWorker

LOG = logging.getLogger(__name__)

# Constants for response meta frame
SE = SERVICE_CALL = b'\x01'
FI = FILES = b'\x02'
TR = TRANSACTIONS = b'\x03'

# Allowed response meta values
META_VALUES = (SE, FI, TR)


class ServiceWorker(ComponentWorker):
    """Service worker task class."""

    @property
    def action(self):
        """Name of service action this service handles.

        :rtype: str

        """

        return self.cli_args['action']

    def get_response_meta(self, payload):
        meta = super().get_response_meta(payload)
        # Add meta for service call when an inter service call is made
        if payload.get('command_reply/result/transport/calls', None):
            meta += SERVICE_CALL

        return meta

    def create_component_instance(self, payload):
        """Create a component instance for current command payload.

        :param payload: Command payload.
        :type payload: `CommandPayload`

        :rtype: `Action`

        """

        # Save transport locally to use it for response payload
        self.__transport = TransportPayload(
            payload.get('command/arguments/transport')
            )

        return Action(
            self.action,
            Payload(payload.get('command/arguments/params')),
            self.__transport,
            self.source_file,
            self.component_name,
            self.component_version,
            self.platform_version,
            variables=self.cli_args.get('var'),
            debug=self.debug,
            )

    def component_to_payload(self, payload, *args, **kwargs):
        """Convert component to a command result payload.

        :params payload: Command payload from current request.
        :type payload: `CommandPayload`
        :params component: The component being used.
        :type component: `Component`

        :returns: A command result payload.
        :rtype: `CommandResultPayload`

        """

        return self.__transport.entity()

    def create_error_payload(self, exc, action, payload):
        # Add error to transport and return transport
        transport = TransportPayload(
            payload.get('command/arguments/transport')
            )
        transport.push(
            'errors/{}/{}'.format(action.get_name(), action.get_version()),
            ErrorPayload.new(str(exc))
            )
        return transport.entity()