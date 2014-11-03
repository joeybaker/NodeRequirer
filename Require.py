import sublime
import sublime_plugin
import os
import json
import re
from os import path

has_rel_path = re.compile("\.?\.?\/")


class RequireCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.files = [
            'assert',
            'buffer',
            'cluster',
            'child_process',
            'crypto',
            'dgram',
            'dns',
            'domain',
            'events',
            'fs',
            'http',
            'https',
            'net',
            'os',
            'path',
            'punycode',
            'readline',
            'stream',
            'string_decoder',
            'tls',
            'url',
            'util',
            'vm',
            'zlib'
        ]
        project_data = sublime.active_window().project_data()
        self.project_folder = project_data['folders'][0]['path']
        self.load_file_list()

        sublime.active_window().show_quick_panel(self.files, self.insert)

    def load_file_list(self):
        self.parse_package_json()
        dirname = path.dirname(self.view.file_name())
        walk = os.walk(self.project_folder)
        for root, dirs, files in walk:
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
            if '.git' in dirs:
                dirs.remove('.git')
            for file_name in files:
                if file_name[0] is not '.':
                    file_name = "%s/%s" % (root, file_name)
                    file_name = path.relpath(file_name, dirname)

                    if file_name == path.basename(self.view.file_name()):
                        continue

                    if not has_rel_path.match(file_name):
                        file_name = "./%s" % file_name

                self.files.append(file_name)

    def parse_package_json(self):
        package = path.join(self.project_folder, 'package.json')
        package_json = json.load(open(package, 'r'))
        dependencyTypes = (
            'dependencies',
            'devDependencies',
            'optionalDependencies'
        )
        for dependencyType in dependencyTypes:
            if dependencyType in package_json:
                self.files += package_json[dependencyType].keys()

    def insert(self, index):
        if index >= 0:
            module = self.files[index]
            position = self.view.sel()[-1].end()
            self.view.run_command('require_insert_helper', {
                'args': {
                    'position': position,
                    'module': module
                }
            })


class RequireInsertHelperCommand(sublime_plugin.TextCommand):
    def run(self, edit, args):
        module = args['module']
        aliases = PluginUtils.get_pref('alias')

        if module in aliases:
            module_name = aliases[module]
        else:
            module_name = path.basename(module)
            module_name, extension = path.splitext(module_name)
            if module.endswith('/index.js'):
                module_name = path.split(path.dirname(module))[-1]
                module = module[:-9]
                if module_name == '' or '.' in module_name:
                    directory = path.dirname(self.view.file_name())
                    module_name = path.split(directory)[-1]

            if module.endswith(".js"):
                module = module[:-3]

            dash_index = module_name.find('-')
            while dash_index > 0:
                first = module_name[:dash_index].capitalize()
                second = module_name[dash_index + 1:].capitalize()
                module_name = '{fst}{snd}'.format(fst=first, snd=second)
                dash_index = module_name.find('-')

        line = self.view.substr(self.view.line(self.view.sel()[0]))
        quotes = "'" if PluginUtils.get_pref('quotes') == 'single' else '"'
        should_add_var = (':' not in line)

        snippet = RequireSnippet(module_name, module, quotes, should_add_var)
        self.view.run_command('insert_snippet', snippet.get_args())


class RequireSnippet():
    def __init__(self, name, path, quotes, should_add_var=True):
        self.name = name
        self.path = path
        self.quotes = quotes
        self.should_add_var = should_add_var

    def get_formatted_code(self):
        formatted_code = 'require({quote}{path}{quote})'.format(
            path=self.path,
            quote=self.quotes
        )
        if self.should_add_var:
            formatted_code = 'var ${{1:{name}}} = {require};'.format(
                name=self.name,
                require=formatted_code
            )
        return formatted_code

    def get_args(self):
        return {
            'contents': self.get_formatted_code()
        }

# Taken from Sublime JSHint Gutter
SETTINGS_FILE = "Require.sublime-settings"


class PluginUtils:
    @staticmethod
    def get_pref(key):
        return sublime.load_settings(SETTINGS_FILE).get(key)
