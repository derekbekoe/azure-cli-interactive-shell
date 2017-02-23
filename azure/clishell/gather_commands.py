import math
import os
import json

from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.completion import Completer, Completion
from azure.clishell.command_tree import CommandBranch, CommandHead
from azure.clishell._dump_commands import get_cache_dir, Configuration

TOLERANCE = 10
LINE_MINIMUM = 30

class GatherCommands(object):
    def __init__(self):
        # everything that is completable
        self.completable = []
        # a completable to the description of what is does
        self.descrip = {}
        # from a command to a list of parameters
        self.command_param = {}

        self.completable_param = []
        self.command_example = {}
        self.command_tree = CommandHead()
        self.param_descript = {}
        self.completer = None
        self.gather_from_files()

    def add_exit(self):
        self.completable.append("quit")
        self.completable.append("exit")

        self.descrip["quit"] = "Exits the program"
        self.descrip["exit"] = "Exits the program"

        self.command_tree.children.append(CommandBranch("quit"))
        self.command_tree.children.append(CommandBranch("exit"))

        self.command_param["quit"] = ""
        self.command_param["exit"] = ""

    def add_random_new_lines(self, long_phrase, line_min):
        if long_phrase is None:
            return long_phrase
        if len(long_phrase) > line_min:
            for num in range(int(math.ceil(len(long_phrase) / line_min))):
                index = (num + 1) * line_min
                while index < len(long_phrase) and \
                not long_phrase[index].isspace() and index < TOLERANCE + line_min:
                    index += 1
                if index < len(long_phrase):
                    if long_phrase[index].isspace():
                        index += 1
                    long_phrase = long_phrase[:index] + "\n" \
                    + long_phrase[index:]
        return long_phrase + "\n"

    def gather_from_files(self):
        command_file = Configuration().get_help_files()

        with open(os.path.join(get_cache_dir(), command_file), 'r') as help_file:
            data = json.load(help_file)

        self.add_exit()
        commands = data.keys()

        for command in commands:
            branch = self.command_tree
            for word in command.split():
                if word not in self.completable:
                    self.completable.append(word)
                if branch.children is None:
                    branch.children = []
                if not branch.has_child(word):
                    branch.children.append(CommandBranch(word))
                branch = branch.get_child(word, branch.children)

            description = data[command]['help']
            self.descrip[command] = self.add_random_new_lines(description, LINE_MINIMUM)

            if 'examples' in data[command]:
                self.command_example[command] = self.add_random_new_lines(
                    data[command]['examples'], int(LINE_MINIMUM * 2.5))

            all_params = []
            for param in data[command]['parameters']:
                suppress = False

                if data[command]['parameters'][param]['help'] and \
                '==SUPPRESS==' in data[command]['parameters'][param]['help']:
                    suppress = True
                if data[command]['parameters'][param]['help'] and not suppress:
                    for par in data[command]['parameters'][param]['name']:
                        self.param_descript[command + " " + par] =  \
                        self.add_random_new_lines(data[command]['parameters'][param]['required']\
                        + " " + data[command]['parameters'][param]['help'], LINE_MINIMUM)
                        if par not in self.completable_param:
                            self.completable_param.append(par)
                        all_params.append(par)

            self.command_param[command] = all_params


        # for command in self.command_example:
        #     print(command + ": " + self.command_example[command])

