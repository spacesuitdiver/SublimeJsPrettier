# -*- coding: utf-8 -*-

from json import dumps
from os import path, environ
from platform import system
from subprocess import PIPE, Popen

import sublime
import sublime_plugin

#
# monkey patch `Region` to be iterable:
sublime.Region.totuple = lambda self: (self.a, self.b)
sublime.Region.__iter__ = lambda self: self.totuple().__iter__()

PLUGIN_NAME = 'JsPrettier'
PLUGIN_PATH = path.join(sublime.packages_path(), path.dirname(path.realpath(__file__)))
SETTINGS_FILE = '{0}.sublime-settings'.format(PLUGIN_NAME)
JS_PRETTIER_FILE = '{0}.js'.format(PLUGIN_NAME.lower())
JS_PRETTIER_PATH = path.join(PLUGIN_PATH, JS_PRETTIER_FILE)


class JsPrettierCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        syntax = self.get_syntax()
        if not syntax:
            return

        if self.view.file_name() is None:
            sublime.error_message(
                '%s Error\n\n'
                'The current view/buffer must be Saved before '
                'running JsPrettier.'
                % PLUGIN_NAME)
            return

        config = self.get_config()
        config['tabWidth'] = self.get_tab_size()

        #
        # format entire file:
        if not self.has_selection():
            region = sublime.Region(0, self.view.size())
            source = self.view.substr(region)
            transformed = self.prettier(source, config)
            if transformed:
                self.view.replace(edit, region, transformed)
                sublime.set_timeout(lambda: sublime.status_message(
                    '{0}: JavaScript formatted.'.format(PLUGIN_NAME)), 0)
            return

        #
        # format each selection:
        for region in self.view.sel():
            if region.empty():
                continue
            source = self.view.substr(region)
            transformed = self.prettier(source, config)
            if transformed:
                self.view.replace(edit, region, transformed)
                sublime.set_timeout(lambda: sublime.status_message(
                    '{0}: JavaScript formatted.'.format(PLUGIN_NAME)), 0)

    def prettier(self, source, config):
        config = dumps(config)
        cwd = path.dirname(self.view.file_name())

        try:
            p = Popen(['node', JS_PRETTIER_PATH, config, cwd],
                      stdout=PIPE, stdin=PIPE, stderr=PIPE,
                      env=self.get_env(), shell=self.is_windows())
        except OSError:
            raise Exception(
                "{0} - node.js program path not found! Please ensure "
                "the path to node.js is set in your $PATH env variable "
                "by running `node -v` from the command-line.".format(PLUGIN_NAME))

        stdout, stderr = p.communicate(input=source.encode('utf-8'))
        if stdout:
            return stdout.decode('utf-8')
        else:
            sublime.error_message(
                "%s Error\n\n"
                "%s"
                % (PLUGIN_NAME, stderr.decode('utf-8')))

    def is_js(self):
        return self.view.scope_name(0).startswith('source.js')

    def get_env(self):
        env = None
        if self.is_osx():
            env = environ.copy()
            env['PATH'] += self.get_node_path()
        return env

    def get_node_path(self):
        return self.get_settings().get('node_path')

    def get_settings(self):
        settings = self.view.settings().get(PLUGIN_NAME)
        if settings is None:
            settings = sublime.load_settings(SETTINGS_FILE)
        return settings

    def get_config(self):
        return self.get_settings().get('config')

    def get_tab_size(self):
        return int(self.view.settings().get('tab_size', 2))

    def has_selection(self):
        for sel in self.view.sel():
            start, end = sel
            if start != end:
                return True
        return False

    @staticmethod
    def get_syntax():
        return 'js'

    @staticmethod
    def is_osx():
        return system() == 'Darwin'

    @staticmethod
    def is_windows():
        return system() == 'Windows'
