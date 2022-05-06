import xml.etree.ElementTree as xml
import os
import shutil
from pathlib import Path
import subprocess
import sys
from .faas_function import FaaSFunction


class Plugin:

    ns = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
          'bpmn2faas': "http://bpmn2faas"}

    def generate(self, path: str, endpoints: [object]):
        for filename in os.listdir(path):
            if filename.endswith('.zip.input'):
                zip_file = filename
                business_code_path = os.path.join(path, zip_file[:-10])
                break

        bpmn_path = os.path.join(path, 'diagram.bpmn')
        root = xml.parse(bpmn_path).getroot()
        pool = root.find('./bpmn2:collaboration/bpmn2:participant', self.ns)
        process = root.find('./bpmn2:process', self.ns)
        lane_set = process.find('./bpmn2:laneSet', self.ns)
        lanes = lane_set.findall('./bpmn2:lane', self.ns)

        # create project folder
        project_name = pool.get('name', default=zip_file[:-10]) + '_aws'
        project_path = os.path.join(path, project_name)
        Path(project_path).mkdir(parents=True, exist_ok=True)

        for lane in lanes:
            faas_function = FaaSFunction(lane, process)

            function_path = os.path.join(project_path, faas_function.name)
            Path(function_path).mkdir(parents=True, exist_ok=True)

            with open(os.path.join(function_path, faas_function.name+'.py'), "w") as function_file:
                function_file.write(faas_function.to_code())

            for module in faas_function.modules:
                source = os.path.join(business_code_path, module)
                destination = os.path.join(function_path, module)
                print(source)
                shutil.copy2(source, destination)

            requirements_path = os.path.join(business_code_path, faas_function.name, 'requirements.txt')

            if os.path.isfile(requirements_path):
                subprocess.check_call([sys.executable, '-m', 'pip', "install", '-r', requirements_path,
                                       '--target', os.path.join(function_path, 'package')])

            shutil.make_archive(function_path, 'zip', function_path)
            shutil.rmtree(function_path)

        shutil.make_archive(project_path, 'zip', project_path)
        shutil.rmtree(project_path)

        return project_path+'.zip'
