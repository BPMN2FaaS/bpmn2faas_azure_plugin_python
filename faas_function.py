import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from .constants.ServiceTypeConstants import Service
from .bpmn import Element
from .bpmn.startevents.StartEvent import StartEvent
from .bpmn.tasks.Task import Task
from .bpmn.tasks.ServiceTask import ServiceTask
from .bpmn.gateways.Gateway import Gateway
from .bpmn.endevents.EndEvent import EndEvent


class FaaSFunction:
    ns = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
          'bpmn2faas': 'http://bpmn2faas'}

    def __init__(self, lane: et.Element, process: et.Element, endpoints: dict):
        self.lane: et.Element = lane
        self.name: str = lane.get('name', default='__init__')

        element_ids: [str] = [node_id.text for node_id in lane.findall('./bpmn2:flowNodeRef', self.ns)]
        elements = [process.find(f'./*[@id="{node_id}"]', self.ns) for node_id in element_ids]

        self.operations: [Element] = []
        self.services: [str] = []

        for element in elements:
            if element.tag == '{' + self.ns['bpmn2'] + '}startEvent':
                self.start_event: StartEvent = StartEvent(element, process)
            elif element.tag == '{' + self.ns['bpmn2'] + '}task':
                task = Task(element, process)
                self.operations.append(task)
            elif element.tag == '{' + self.ns['bpmn2'] + '}serviceTask':
                st = ServiceTask(element, process)
                st.connection_string = endpoints.get(st.id, '')
                self.operations.append(st)
                if st.service not in self.services:
                    self.services.append(st.service)
            elif element.tag == '{' + self.ns['bpmn2'] + '}exclusiveGateway':
                gateway = Gateway(element, process, endpoints)
                if gateway.is_splitting:
                    self.operations.append(gateway)
            elif element.tag == '{' + self.ns['bpmn2'] + '}endEvent':
                self.operations.append(EndEvent(element, process))
        self.operations = self.__get_sequence()

        serviceBus_client_imported = False
        for i in range(0, len(self.services)):
            if self.services[i] == Service.OBJECT_STORAGE:
                self.services[i] = 'from azure.storage.blob import BlobServiceClient, ContainerClient'
            elif self.services[i] == Service.QUEUE:
                self.services[i] = 'from azure.storage.queue import QueueServiceClient, QueueClient'
            elif (self.services[i] == Service.FIFO_QUEUE or self.services[i] == Service.PUBSUB) and not serviceBus_client_imported:
                self.services[i] = 'from azure.servicebus.management import ServiceBusAdministrationClient\n' \
                                   'from azure.servicebus import ServiceBusClient, ServiceBusSender, ServiceBusReceiver, ServiceBusMessage'
                serviceBus_client_imported = True

        self.modules: [str] = self.__get_modules()

    def __get_sequence(self) -> [Element]:
        sequence = [self.start_event]
        while self.operations:
            index = 0
            for op in self.operations:
                if type(sequence[-1]) is Gateway and sequence[-1].is_splitting:
                    if sequence[-1].joining_gateway.outgoing and \
                            sequence[-1].joining_gateway.outgoing[0].get('id') == op.id:
                        sequence.append(op)
                    self.operations.pop(index)
                    break
                elif sequence[-1].outgoing[0].get('id') == op.id:
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

    def to_code(self) -> str:
        template_folder = os.path.join(os.path.dirname(__file__), 'templates')
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader)
        template = env.get_template('function.py.jinja')
        data = {'modules': self.modules,
                'clients': self.services,
                'input_class': self.start_event.input_class,
                'operations': self.operations,
                'start_event': self.start_event}

        return template.render(data=data)
