import xml.etree.ElementTree as et
from jinja2 import Environment, FileSystemLoader
import os
from ..Element import Element


class EndEvent(Element):
    def __init__(self, element: et.Element, process: et.Element):
        super(EndEvent, self).__init__(element, process)

        namespace = '{' + self.ns['bpmn2faas'] + '}'

        self.return_literal: str = element.get(namespace + 'return')

    def to_code(self) -> str:
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), '../../templates'))
        env = Environment(loader=file_loader)
        template = env.get_template(f'return.jinja')
        data = {'return': self.return_literal}

        return template.render(data=data)
