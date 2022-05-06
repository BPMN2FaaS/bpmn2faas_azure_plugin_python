import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from ..Element import Element
from pathlib import Path


class Task(Element):

    def __init__(self, element: et.Element, process: et.Element):
        super(Task, self).__init__(element, process)

        namespace = '{'+self.ns['bpmn2faas']+'}'
        module_function = element.get(namespace+'function').split(':')

        self.module: str = module_function[0]
        self.function: str = module_function[1]
        self.args: [str] = []
        for i in range(1, 6):
            arg = element.get(f'{namespace}arg{i}', default=None)
            if arg is not None:
                self.args.append(arg)
        self.is_loop: bool = True if element.find('./bpmn2:standardLoopCharacteristics', self.ns) is not None else False
        self.loop_condition: str = element.get(namespace+'for') if self.is_loop else None

    def to_code(self) -> str:
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), '../../templates'))
        env = Environment(loader=file_loader)
        template = env.get_template('business_function.jinja')
        data = {'task_name': self.name if self.name is not None else self.id,
                'module': Path(self.module).stem,
                'function': self.function,
                'args': ', '.join(self.args),
                'is_loop': self.is_loop}
        if self.is_loop:
            data['loop_condition'] = self.loop_condition
        return template.render(data=data)
