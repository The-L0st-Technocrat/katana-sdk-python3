from ..service.server import ServiceServer

from .component import Component
from .runner import ComponentRunner


class Service(Component):
    """KATANA SDK Service component."""

    def __init__(self):
        super().__init__()
        self._runner = ComponentRunner(
            ServiceServer,
            'Service component action to process application logic',
            )

    def run_action(self, callback):
        self.run(callback)