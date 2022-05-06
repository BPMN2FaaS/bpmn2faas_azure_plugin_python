import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from .constants.ServiceTypeConstants import Service
from .bpmn import Element
from .bpmn.startevents.StartEvent import StartEvent
from .bpmn.tasks.Task import Task
from .bpmn.tasks.ServiceTask import ServiceTask


class FaaSFunction:
    ns = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
          'bpmn2faas': 'http://bpmn2faas'}

    def __init__(self, lane: et.Element, process: et.Element):
        self.lane: et.Element = lane
        self.name: str = lane.get('name')

        element_ids: [str] = [node_id.text for node_id in lane.findall('./bpmn2:flowNodeRef', self.ns)]
        elements = [process.find(f'./*[@id="{node_id}"]', self.ns) for node_id in element_ids]

        self.operations: [Element] = []
        self.services: [str] = []
        for element in elements:
            if element.tag == '{'+self.ns['bpmn2']+'}startEvent':
                self.start_event: StartEvent = StartEvent(element, process)
            elif element.tag == '{'+self.ns['bpmn2']+'}task':
                self.operations.append(Task(element, process))
            elif element.tag == '{'+self.ns['bpmn2']+'}serviceTask':
                st = ServiceTask(element, process)
                self.operations.append(st)
                if st.service not in self.services:
                    self.services.append(st.service)
        self.operations = self.__get_sequence()

        for i in range(0, len(self.services)):
            if self.services[i] == Service.OBJECT_STORAGE:
                self.services[i] = 's3'
            elif self.services[i] == Service.QUEUE or self.services[i] == Service.FIFO_QUEUE:
                self.services[i] = 'sqs'
            elif self.services[i] == Service.PUBSUB:
                self.services[i] = 'sns'

        self.modules: [str] = self.__get_modules()

    def to_code(self) -> str:
        template_folder = os.path.join(os.path.dirname(__file__), 'templates')
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader)
        template = env.get_template('function.py.jinja')
        data = {'modules': self.modules,
                'clients': self.services,
                'handler_name': 'handler',
                'operations': self.operations,
                'start_event': self.start_event}

        return template.render(data=data)

    def __get_sequence(self) -> [Element]:
        sequence = [self.start_event]
        while self.operations:
            index = 0
            for op in self.operations:
                if sequence[-1].outgoing[0] == op.id:
                    sequence.append(op)
                    self.operations.pop(index)
                    break
                index += 1
        return sequence[1:]

    def __get_modules(self) -> [str]:
        modules = []
        for op in self.operations:
            if type(op) is Task and op.module not in modules:
                modules.append(op.module)
        return modules
