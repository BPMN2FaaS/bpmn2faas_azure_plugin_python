import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from ..Element import Element
from ..tasks.Task import Task
from ..tasks.ServiceTask import ServiceTask
from ..endevents.EndEvent import EndEvent


class Gateway(Element):
    def __init__(self, element: et.Element, process: et.Element, endpoints: dict):
        super(Gateway, self).__init__(element, process)

        namespace = '{' + self.ns['bpmn2faas'] + '}'

        self.endpoints: dict = endpoints
        self.is_splitting: bool = False
        if len(self.incoming) == 1 and len(self.outgoing) > 1:
            self.is_splitting = True
            self.condition = element.get(namespace+'condition')
            if len(self.outgoing) == 2:
                self.mode = 'if'
            elif len(self.outgoing) > 2:
                self.mode = 'switch'

            branches: [[Element]] = self.__get_branches(process)

            arrows = process.findall(f'./bpmn2:sequenceFlow[@sourceRef="{self.id}"]', self.ns)
            self.cases: [str] = [arrow.get(namespace + 'case') for arrow in arrows]

            self.branches: [[Element]] = []
            default_branch_index = 0
            for arrow in arrows:
                index = 0
                for branch in branches:
                    if branch[0].id == arrow.get('targetRef'):
                        if arrow.get(namespace + 'defaultBranch') is not None and arrow.get(namespace + 'defaultBranch') == 'true':
                            default_branch_index = index
                        else:
                            self.branches.append(branch)
                    index += 1

            self.has_default: bool = False
            for arrow in arrows:
                if arrow.get(namespace + 'defaultBranch') is not None and arrow.get(namespace + 'defaultBranch') == 'true':
                    self.has_default = True
                    self.cases.pop(default_branch_index)
                    self.branches.append(branches[default_branch_index])
                    break

    def __get_branches(self, process: et.Element) -> [[Element]]:
        branches = []

        for next_element in self.outgoing:
            branch = []
            element = next_element
            while True:
                if element.tag == '{' + self.ns['bpmn2'] + '}task':
                    element = Task(element, process)
                elif element.tag == '{' + self.ns['bpmn2'] + '}serviceTask':
                    element = ServiceTask(element, process)
                    element.connection_string = self.endpoints.get(element.id, '')
                elif element.tag == '{' + self.ns['bpmn2'] + '}endEvent':
                    element = EndEvent(element, process)
                elif element.tag == '{' + self.ns['bpmn2'] + '}exclusiveGateway':
                    element = Gateway(element, process, self.endpoints)

                if type(element) is Task or type(element) is ServiceTask or type(element) is EndEvent:
                    branch.append(element)
                    if element.outgoing[0] is not None:
                        element = element.outgoing[0]
                    else:
                        break
                elif type(element) is Gateway:
                    if element.is_splitting:
                        branch.append(element)
                        if element.joining_gateway.outgoing[0] is not None:
                            element = element.joining_gateway.outgoing[0]
                        else:
                            break
                    else:
                        self.joining_gateway = element
                        break

            branches.append(branch)

        return branches

    def to_code(self) -> str:
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), '../../templates'))
        env = Environment(loader=file_loader)
        template = env.get_template(f'{self.mode}.jinja')

        for branch in self.branches:
            for op in branch:
                op.indentation = self.indentation + 1

        data = {'condition': self.condition,
                'cases': self.cases,
                'operations': self.branches,
                'hasDefault': self.has_default}

        return template.render(data=data, op=self)
