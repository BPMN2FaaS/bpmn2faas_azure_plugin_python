import xml.etree.ElementTree as et


class Element:
    ns = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
          'bpmn2faas': 'http://bpmn2faas'}

    def __init__(self, element: et.Element, process: et.Element):
        self.xml = element
        self.id: str = element.get('id')
        self.name: str = element.get('name', default=None)
        self.incoming: [et.Element] = self.__get_incoming_elements(process)
        self.outgoing: [et.Element] = self.__get_outgoing_elements(process)

    def __get_incoming_elements(self, process: et.Element) -> [et.Element]:
        arrows = process.findall(f'./bpmn2:sequenceFlow[@targetRef="{self.id}"]', self.ns)
        return [process.find('./*[@id="'+arrow.attrib['sourceRef']+'"]', self.ns).get('id') for arrow in arrows]

    def __get_outgoing_elements(self, process: et.Element) -> [et.Element]:
        arrows = process.findall(f'./bpmn2:sequenceFlow[@sourceRef="{self.id}"]', self.ns)
        return [process.find('./*[@id="'+arrow.attrib['targetRef']+'"]', self.ns).get('id') for arrow in arrows]

    def to_code(self) -> str:
        pass
