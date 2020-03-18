import os
import sys
import traceback
from . import events
from . import windows
from . import irc
from . import widgets

urkpath = os.path.abspath(os.path.dirname(__file__))

if os.path.abspath(os.curdir) != os.path.join(urkpath):
    sys.path[0] = os.path.join(urkpath)

sys.path = [
    os.path.join(urkpath, "scripts"),
] + sys.path

script_path = urkpath + "/scripts"

from .ui import *


# Here I'm trying to handle the original URL IRC Client, urk don't use
# normal classes . Let's try to get an Urk Widget:
class Trigger(object):

    def __init__(self):
        self._mods = []
        self.events = events
        self._load_scripts()

    def _load_scripts(self):
        script_path = urkpath + "/scripts"
        print(f"script path: {script_path}")
        try:
            suffix = os.extsep + "py"
            for script in os.listdir(script_path):
                if script.endswith(suffix):
                    try:
                        mod = self.events.load(script)
                        self._mods.append(mod)
                    except:
                        traceback.print_exc()
                        print("Failed loading script %s." % script)
        except OSError:
            pass

    def get_modules(self):
        return self._mods


class Core(object):

    def __init__(self, activity):
        self.window = None
        self.trigger = Trigger()
        self.events = self.trigger.events
        self.manager = widgets.UrkUITabs(self)
        self.channels = []

        mods = self.trigger.get_modules()

        for m in mods:
            m.core = self
            m.manager = self.manager

        if not self.window:
            self.window = windows.new(
                windows.StatusWindow,
                irc.Network(self, activity),
                "status",
                self)
            self.window.activate()

    def run_command(self, command):
        offset = 0
        if command[0] == '/':
            offset = 1

        self.events.run(
            command[
                offset:],
            self.manager.get_active(),
            self.window.network)

    def trigger_start(self):
        self.events.trigger("Start")

    def _add_script(self, module):
        return


class Client(object):

    def __init__(self, activity):
        self.core = Core(activity)
        self.widget = self.core.manager
        self.widget.show_all()

    def run_command(self, command):
        self.core.run_command(command)

    def join_server(self, network_name, port=8001):
        command = 'server ' + network_name + ' ' + str(port)
        self.run_command(command)

    def get_widget(self):
        return self.widget

    def show(self):
        self.widget.show_all()

    def add_channel(self, channel):
        print("** DEBUG :: Add default channel: ", channel)
        self.core.channels.append(channel)

    def add_channel_other(self, channelother):
        print("** DEBUG :: Add default channel other: ", channelother)
        self.core.channels.append(channelother)

    def clear_channels(self):
        self.core.channels = []
