import xml.etree.ElementTree as xml
import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from .faas_function import FaaSFunction
from .constants.TriggerTypeConstants import Trigger


class Plugin:

    ns = {'bpmn2': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
          'bpmn2faas': "http://bpmn2faas"}

    def generate(self, path: str, endpoints: dict):
        zip_file = ''
        for filename in os.listdir(path):
            if filename.endswith('.zip.input'):
                zip_file = filename

        business_code_path = os.path.join(path, zip_file[:-10])
        bpmn_path = os.path.join(path, 'diagram.bpmn')
        root = xml.parse(bpmn_path).getroot()
        pool = root.find('./bpmn2:collaboration/bpmn2:participant', self.ns)
        process = root.find('./bpmn2:process', self.ns)
        lane_set = process.find('./bpmn2:laneSet', self.ns)
        lanes = lane_set.findall('./bpmn2:lane', self.ns)

        # create project folder
        project_name = pool.get('name', default=zip_file[:-10]) + '_azure'
        project_path = os.path.join(path, project_name)
        Path(project_path).mkdir(parents=True, exist_ok=True)

        functions: [FaaSFunction] = []
        requirements = []

        for lane in lanes:
            faas_function = FaaSFunction(lane, process, endpoints)
            functions.append(faas_function)

            function_path = os.path.join(project_path, faas_function.name)
            Path(function_path).mkdir(parents=True, exist_ok=True)

            with open(os.path.join(function_path, faas_function.name+'.py'), 'w') as function_file:
                function_file.write(faas_function.to_code())

            shared_modules_path = os.path.join(project_path, 'shared_code')
            Path(shared_modules_path).mkdir(parents=True, exist_ok=True)

            for module in os.listdir(business_code_path):
                if module.endswith('.py'):
                    source = os.path.join(business_code_path, module)
                    destination = os.path.join(shared_modules_path, module)
                    shutil.copy2(source, destination)

            requirements_path = os.path.join(business_code_path, faas_function.name, 'requirements.txt')

            if os.path.isfile(requirements_path):
                with open(requirements_path, 'r') as requirements_file:
                    requirements += requirements_file.readlines()
                    if not requirements[-1].endswith('\n'):
                        requirements[-1] += '\n'

            # generate function.json
            trigger_type = ''
            schedule = ''

            if faas_function.start_event.trigger_type == Trigger.OBJECT_STORAGE:
                trigger_type = 'blobTrigger'
            elif faas_function.start_event.trigger_type == Trigger.TIMER:
                trigger_type = 'timerTrigger'
                schedule = faas_function.start_event.schedule
            elif faas_function.start_event.trigger_type == Trigger.QUEUE:
                trigger_type = 'queueTrigger'
            elif faas_function.start_event.trigger_type == Trigger.PUBSUB or \
                    faas_function.start_event.trigger_type == Trigger.FIFO_QUEUE:
                trigger_type = 'serviceBusTrigger'

            template_folder = os.path.join(os.path.dirname(__file__), 'templates')
            file_loader = FileSystemLoader(template_folder)
            env = Environment(loader=file_loader)
            template = env.get_template('function.json.jinja')
            bindings = {'function_name': faas_function.name+'.py',
                        'trigger_type':  trigger_type,
                        'schedule':      schedule,
                        'queue_name':    faas_function.start_event.name,
                        'connection':    faas_function.start_event.name+'_'+faas_function.start_event.trigger_type.name}

            with open(os.path.join(function_path, 'function.json'), 'w') as function_bindings:
                function_bindings.write(template.render(data=bindings))

        requirements = set(requirements)
        with open(os.path.join(project_path, 'requirements.txt'), 'w') as requirements_file:
            requirements_file.write('azure-functions\n\n')
            requirements_file.write(''.join(requirements))

        connection_strings = []
        for function in functions:
            if function.start_event.trigger_type is not Trigger.TIMER:
                connection_strings.append({'event_source':      function.start_event.name,
                                           'service_type':      function.start_event.trigger_type.name,
                                           'connection_string': endpoints[function.start_event.id]})

        # eliminate duplicates
        connection_strings = list(map(dict, set(tuple(sorted(cs.items())) for cs in connection_strings)))

        template_folder = os.path.join(os.path.dirname(__file__), 'templates')
        file_loader = FileSystemLoader(template_folder)
        env = Environment(loader=file_loader)
        template = env.get_template('local.settings.json.jinja')
        with open(os.path.join(project_path, 'local.settings.json'), 'w') as local_settings_file:
            local_settings_file.write(template.render(data=connection_strings))

        host_path = os.path.join(os.path.dirname(__file__), 'resources', 'host.json')
        funcignore_path = os.path.join(os.path.dirname(__file__), 'resources', 'funcignore_file')
        shutil.copy2(host_path, os.path.join(project_path, 'host.json'))
        shutil.copy2(funcignore_path, os.path.join(project_path, '.funcignore'))
        shutil.make_archive(project_path, 'zip', project_path)
        shutil.rmtree(project_path)

        return project_path+'.zip'
