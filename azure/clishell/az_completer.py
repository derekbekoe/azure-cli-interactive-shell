import math
import os
import argcomplete
import sys
import json
import os
import pkgutil
import yaml
import os, sys, argparse, contextlib

from importlib import import_module
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.completion import Completer, Completion

from argcomplete import completers, my_shlex as shlex
from argcomplete.compat import USING_PYTHON2, str, sys_encoding, ensure_str, ensure_bytes
from argcomplete.completers import FilesCompleter
from argcomplete.my_argparse import IntrospectiveArgumentParser, action_is_satisfied, action_is_open, action_is_greedy

from azure.cli.core.parser import AzCliCommandParser

from azure.cli.core.application import APPLICATION, Application, Configuration
from azure.clishell.gather_commands import GatherCommands

from azure.clishell.completion_finder import CompletionFinder as MyCompleterFinder, FilesCompleter
from azure.cli.core.application import APPLICATION, Application, Configuration
from azure.cli.core.commands import CliArgumentType
from azure.cli.core.commands import load_params, _update_command_definitions
from azure.clishell.configuration import get_config_dir, Configuration
from azure.cli.core.help_files import helps
from azure.cli.core.application import APPLICATION


class AzCompleter(Completer):
    """ Completes Azure CLI commands """
    def __init__(self):
        commands = GatherCommands()
        # a completable to the description of what is does
        self.command_description = commands.descrip
        self.completable = commands.completable
        # from a command to a list of parameters
        self.command_parameters = commands.command_param
        self.completable_param = commands.completable_param

        self.command_tree = commands.command_tree
        self.param_description = commands.param_descript
        self.command_examples = commands.command_example



        self.global_parser = AzCliCommandParser(prog='az', add_help=False)
        global_group = self.global_parser.add_argument_group('global', 'Global Arguments')
        # self.raise_event(self.GLOBAL_PARSER_CREATED, global_group=global_group)

        self.parser = AzCliCommandParser(prog='az', parents=[self.global_parser])
        cmd_table = APPLICATION.configuration.get_command_table()
        for cmd in cmd_table:
            cmd_table[cmd].load_arguments()

        try:
            mods_ns_pkg = import_module('azure.cli.command_modules')
            installed_command_modules = [modname for _, modname, _ in
                                         pkgutil.iter_modules(mods_ns_pkg.__path__)]
        except ImportError:
            pass
        for mod in installed_command_modules:
            # print('loading params for', mod)
            try:
                import_module('azure.cli.command_modules.' + mod).load_params(mod)
            except Exception as ex:
                print("EXCPETION: " + ex.message)
        _update_command_definitions(cmd_table)

        self.parser.load_command_table(cmd_table)
        self.cmdtab = cmd_table

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        command = ""
        is_command = True
        branch = self.command_tree
        if text_before_cursor.split():
            if text_before_cursor.split()[0] == 'az':
                text_before_cursor = ' '.join(text_before_cursor.split()[1:])
            if text_before_cursor.split():
                for words in text_before_cursor.split():
                    if words.startswith("-") and not words.startswith("--"):
                        is_command = False
                        if self.has_parameters(command):
                            for param in self.get_param(command):
                                if param.lower().startswith(words.lower()) and \
                                param.lower() != words.lower() and not param.startswith("--") and\
                                param not in text_before_cursor.split():
                                    yield Completion(param, -len(words), display_meta=\
                                    self.get_param_description(command + " " + str(param)))

                    if words.startswith("--"):
                        is_command = False
                        if self.has_parameters(command):
                            for param in self.get_param(command):
                                if param.lower().startswith(words.lower()) and \
                                param.lower() != words.lower() and\
                                param not in text_before_cursor.split():
                                    yield Completion(param, -len(words),\
                                    display_meta=self.get_param_description(
                                        command + " " + str(param)))
                        else:
                            for param in self.completable_param:
                                if param.lower().startswith(words.lower()) and \
                                param.lower() != words.lower() and\
                                param not in text_before_cursor.split():
                                    if command + " " + str(param) in self.param_description:
                                        yield Completion(param, -len(words),\
                                        display_meta=self.get_param_description(\
                                        command + " " + str(param)))
                                    else:
                                        yield Completion(param, -len(words))
                    else:
                        if is_command:
                            if command:
                                command += " " + str(words)
                            else:
                                command += str(words)
                        try:
                            if branch.has_child(words):
                                branch = branch.get_child(words, branch.children)
                        except ValueError:
                            continue # do something

                if branch.children is not None:
                    for kid in branch.children:
                        if kid.data.lower().startswith(text_before_cursor.split()[-1].lower()):
                            yield Completion(str(kid.data),\
                                -len(text_before_cursor.split()[-1]))

        if not text_before_cursor.split() or text_before_cursor[-1] == " ":
            if branch.children is not None:
                for com in branch.children:
                    yield Completion(com.data)

        is_param = False
        param = ""
        if text_before_cursor.split():
            param = text_before_cursor.split()[-1]
            if param.startswith("-"):
                is_param = True

        arg_name = ""
        if command in self.cmdtab:
            if is_param:
                for arg in self.cmdtab[command].arguments:
                    for name in self.cmdtab[command].arguments[arg].options_list:
                        if name == param:
                            arg_name = arg
                            break
                    if arg_name:
                        break
                if arg_name:
                    if self.cmdtab[command].arguments[arg_name].completer:
                        # formats = []
                        # for form in formats:
                        try:
                            for comp in self.cmdtab[command].\
                            arguments[arg_name].completer("", None, command):
                                yield Completion(comp)
                        except TypeError:
                            try:
                                for comp in self.cmdtab[command].\
                                arguments[arg_name].completer(""):
                                    yield Completion(comp)
                            except TypeError:
                                try:
                                    for comp in self.cmdtab[command].\
                                    arguments[arg_name].completer():
                                        yield Completion(comp)
                                except TypeError:
                                    print("TypeError: " + TypeError.message)



    def is_completable(self, command):
        """ whether the command can be completed """
        return self.has_parameters(command) or command in self.param_description.keys()

    def get_param(self, command):
        """ returns the parameters for a given command """
        return self.command_parameters[command]

    def get_param_description(self, param):
        """ gets a description of an empty string """
        if param in self.param_description:
            return self.param_description[param]
        else:
            return ""

    def get_description(self, command):
        """ returns the description for a given command """
        return self.command_description[command]

    def has_parameters(self, command):
        """ returns whether given command is valid """
        return command in self.command_parameters.keys()

    def get_all_subcommands(self):
        """ returns all the subcommands """
        subcommands = []
        for command in self.command_description:
            for word in command.split():
                for kid in self.command_tree.children:
                    if word != kid.data and word not in subcommands:
                        subcommands.append(word)
        return subcommands

    def has_description(self, param):
        """ if a parameter has a description """
        return param in self.param_description.keys() and \
        not self.param_description[param].isspace()
