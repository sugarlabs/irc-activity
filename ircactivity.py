# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
# Copyright (C) 2012, Aneesh Dogra <lionaneesh@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk

import json
import ConfigParser
import os

from sugar3.activity import activity
from sugar3.activity.activity import get_bundle_path
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import StopButton, TitleEntry, ActivityButton

import purk
import purk.conf
import purk.windows

DEFAULT_CONFIG_PATH = os.path.join(get_bundle_path(), 'irc_config.cfg')
ETC_CONFIG_PATH = os.path.join('/', 'etc', 'irc_config.cfg')
I18N_CHANNELS = ["#sugar", "#sugar-es"]


class IRCActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

        logging.debug('Starting the IRC Activity')
        self.set_title(_('IRC Activity'))

        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event',
                     self.__visibility_notify_event_cb)

        self.is_visible = False

        self.client = purk.Client()
        if handle.object_id is None:
            self.default_config()
        self.client.show()
        widget = self.client.get_widget()

        # CANVAS
        self.set_canvas(widget)

        toolbar_box = ToolbarBox()
        self.activity_button = ActivityButton(self)
        toolbar_box.toolbar.insert(self.activity_button, 0)
        self.activity_button.show()

        title_entry = TitleEntry(self)
        toolbar_box.toolbar.insert(title_entry, -1)
        title_entry.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

    def __visibility_notify_event_cb(self, window, event):
        self.is_visible = event.state != Gdk.VisibilityState.FULLY_OBSCURED

        # Configuracion por defecto

    def default_config(self):
        if os.path.exists(ETC_CONFIG_PATH):
            self.read_defaults_from_config(ETC_CONFIG_PATH)
        elif os.path.exists(DEFAULT_CONFIG_PATH):
            data = self.read_defaults_from_config(DEFAULT_CONFIG_PATH)
            if not data["server"]:
                self.client.join_server('irc.freenode.net')
            if not data["channels"]:
                self.i18n_channels()
        else:
            self.client.join_server('irc.freenode.net')
            self.i18n_channels()

    def i18n_channels(self):
        locale = os.environ["LANG"]
        channels = ["#sugar"]
        if locale:
            locale = locale.split("_")[0]
            if locale != "en":
                channel = "#sugar-%s" % locale
                channels.append(channel)

        for channel in channels:
            if channel in I18N_CHANNELS:
                self.client.add_channel(channel)

    def read_defaults_from_config(self, config_file):
        logging.debug('Reading configuration from file %s' % config_file)
        fp = open(config_file)
        config = ConfigParser.ConfigParser()
        try:
            config.readfp(fp)
            fp.close()
        except Exception as error:
            logging.debug('Reading configuration, error: %s' % error)
            fp.close()
            return {"server": None, "channels": None}

        DATA = {"server": None, "chanels": None}
        if config.has_section('Config'):
            if config.has_option('Config', 'Nick'):
                nick = config.get('Config', 'Nick').strip()
                self.client.run_command('NICK %s' % (nick))
            if config.has_option('Config', 'Server'):
                server = config.get('Config', 'Server').strip()
                self.client.join_server(server)
                DATA["server"] = server
            if config.has_option('Config', 'Channels'):
                channels = config.get('Config', 'Channels').split(',')
                DATA["channels"] = channels
                for channel in channels:
                    self.client.add_channel(channel.strip())
                    self.client.add_channel_other(channel.strip())

        return DATA

    def read_file(self, file_path):
        if self.metadata['mime_type'] != 'text/plain':
            return

        fd = open(file_path, 'r')
        text = fd.read()
        data = json.loads(text)
        fd.close()

        self.client.run_command('NICK %s' % (data['nick']))

        self.client.join_server(data['server'])
        for chan in data['channels']:
            self.client.add_channel(chan)
            self.client.add_channel_other(chan)
        self.client.core.window.network.requested_joins = set()
        for winid in data['scrollback'].keys():
            if winid in data['channels']:
                win = purk.windows.new(purk.windows.ChannelWindow,
                                       self.client.core.window.network,
                                       winid, self.client.core)
            else:
                win = purk.windows.new(purk.windows.QueryWindow,
                                       self.client.core.window.network,
                                       winid, self.client.core)
            win.output.get_buffer().set_text(data['scrollback'][winid])
            if winid == data['current-window']:
                self.client.core.window.network.requested_joins = set([winid])

    def write_file(self, file_path):
        if not self.metadata['mime_type']:
            self.metadata['mime_type'] = 'text/plain'

        data = {}
        data['nick'] = self.client.core.window.network.me
        data['server'] = self.client.core.window.network.server
        data['username'] = self.client.core.window.network.server
        data['fullname'] = self.client.core.window.network.fullname
        data['password'] = self.client.core.window.network.password
        data['current-window'] = self.client.core.manager.get_active().id
        data['channels'] = []
        data['scrollback'] = {}

        for i in range(self.client.core.manager.tabs.get_n_pages()):
            win = self.client.core.manager.tabs.get_nth_page(i)
            if win.id == "status":
                continue
            if win.is_channel():
                data['channels'].append(win.id)
            buf = win.output.get_buffer()
            data['scrollback'][
                win.id] = buf.get_text(
                buf.get_start_iter(),
                buf.get_end_iter(),
                True)

        fd = open(file_path, 'w')
        text = json.dumps(data)
        fd.write(text)
        fd.close()
