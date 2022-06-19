import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from ..Element import Element
from ...constants.ServiceTypeConstants import Service


class ServiceTask(Element):

    def __init__(self, element: et.Element, process: et.Element):
        super(ServiceTask, self).__init__(element, process)

        namespace = '{' + self.ns['bpmn2faas'] + '}'

        if element.get(namespace+'service') == 'objectStorage':
            self.service: Service = Service.OBJECT_STORAGE
        elif element.get(namespace+'service') == 'queue':
            if element.get(namespace+'fifo') == 'true':
                self.service: Service = Service.FIFO_QUEUE
            else:
                self.service: Service = Service.QUEUE
        elif element.get(namespace+'service') == 'fifoQueue':
            self.service: Service = Service.FIFO_QUEUE
        elif element.get(namespace+'service') == 'pubsub':
            self.service: Service = Service.PUBSUB

        self.service_call: str = element.get(namespace+'serviceCall')
        self.connection_string: str = ''
        self.args: [str] = [element.get(f'{namespace}arg{i}', default=None) for i in range(1, 6)]
        self.is_loop: bool = True if element.find('./bpmn2:standardLoopCharacteristics', self.ns) is not None else False
        self.loop_condition: str = element.get(namespace+'for') if self.is_loop else None

    def to_code(self) -> str:
        template_folder = os.path.join(os.path.dirname(__file__), '../../templates')
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader)
        template = env.get_template(f'servicecalls/{self.service.value}/{self.service_call}.jinja')
        data = {'task_name': self.name if self.name is not None else self.id,
                'args': self.args,
                'connection_string': self.connection_string,
                'is_loop': self.is_loop}
        if self.is_loop:
            data['loop_condition'] = self.loop_condition
        return template.render(data=data, op=self)
