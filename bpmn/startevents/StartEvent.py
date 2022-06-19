import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from ..Element import Element
from ...constants.TriggerTypeConstants import Trigger


class StartEvent(Element):
    def __init__(self, element: et.Element, process: et.Element):
        super(StartEvent, self).__init__(element, process)

        namespace = '{' + self.ns['bpmn2faas'] + '}'

        if element.find('./bpmn2:timerEventDefinition', self.ns) is not None:
            self.trigger_type: Trigger = Trigger.TIMER
            self.input_class: str = 'TimerRequest'
            self.schedule: str = element.get(namespace+'schedule')
        else:
            if element.get(namespace+'trigger') == 'objectStorage':
                self.trigger_type: Trigger = Trigger.OBJECT_STORAGE
                self.input_class: str = 'InputStream'
            elif element.get(namespace+'trigger') == 'documentStore':
                self.trigger_type: Trigger = Trigger.DOCUMENT_STORE
                self.input_class: str = 'DocumentList'
            elif element.get(namespace+'trigger') == 'queue':
                if element.get(namespace+'fifo') == 'true':
                    self.trigger_type: Trigger = Trigger.FIFO_QUEUE
                    self.input_class: str = 'ServiceBusMessage'
                else:
                    self.trigger_type: Trigger = Trigger.QUEUE
                    self.input_class: str = 'QueueMessage'
            elif element.get(namespace+'trigger') == 'fifoQueue':
                self.trigger_type: Trigger = Trigger.FIFO_QUEUE
                self.input_class: str = 'ServiceBusMessage'
            elif element.get(namespace+'trigger') == 'pubsub':
                self.trigger_type: Trigger = Trigger.PUBSUB
                self.input_class: str = 'ServiceBusMessage'
            elif element.get(namespace+'trigger') == 'timer':
                self.trigger_type: Trigger = Trigger.TIMER
                self.input_class: str = 'TimerRequest'
                self.schedule: str = element.get(namespace+'schedule')

    def to_code(self) -> str:
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), '../../templates'))
        env = Environment(loader=file_loader)
        template = env.get_template(f'eventschemas/{self.trigger_type.value}_schema.jinja')
        return template.render(eventSource=self.name)
