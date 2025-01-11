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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
# MA 02110-1301  USA

import json
import configparser
import os

import gi
gi.require_version('Gtk', '3.0')

import logging
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from sugar3.activity import activity
from sugar3.activity.activity import get_bundle_path
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
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
        self._theme_colors = {
            "light": {
                'fg_color': '#000000',
                'bg_color': '#FFFFFF'
                },
            "dark": {
                'fg_color': '#FFFFFF',
                'bg_color': '#000000'}}
        self._theme_state = "light"
        self.tab_themes = {}
        self.no_of_tabs = 0

        logging.debug('Starting the IRC Activity')
        self.set_title(_('IRC Activity'))

        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event',
                     self.__visibility_notify_event_cb)

        self.is_visible = False

        self.client = purk.Client(self)
        window = self.client.get_widget().get_active()
        font_desc = window.get_pango_context().get_font_description()
        self.original_zlevel= font_desc.get_size()

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

        connectionbtn = ToggleToolButton('connect')
        connectionbtn.set_active(True)
        connectionbtn.set_tooltip(_('Disconnect'))
        connectionbtn.connect('toggled', self._connection_cb)
        toolbar_box.toolbar.insert(connectionbtn, -1)
        connectionbtn.show()

        sep = Gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(sep, -1)
        sep.show()

        # a light and dark theme button
        self._theme_toggler = ToolButton('dark-theme')
        self._theme_toggler.set_tooltip('Switch to Dark Theme')
        self._theme_toggler.props.accelerator = '<Ctrl><Shift>I'
        self._theme_toggler.connect('clicked', self._toggled_theme)
        toolbar_box.toolbar.insert(self._theme_toggler, -1)
        self._theme_toggler.show()

        # Button for zoom out
        self.zoom_out = ToolButton('zoom-out', accelerator='<ctrl>minus')
        self.zoom_out.set_tooltip(_('Zoom out'))
        self.zoom_out.connect('clicked', self.__zoom_out_cb)
        toolbar_box.toolbar.insert(self.zoom_out, -1)
        self.zoom_out.show()

        # Button for zoom in
        self.zoom_in = ToolButton('zoom-in', accelerator='<ctrl>plus')
        self.zoom_in.set_tooltip(_('Zoom in'))
        self.zoom_in.connect('clicked', self.__zoom_in_cb)
        toolbar_box.toolbar.insert(self.zoom_in, -1)
        self.zoom_in.show()

        self.zoom_original = ToolButton('zoom-original', accelerator='<ctrl>0')
        self.zoom_original.set_tooltip(_('Actual size'))
        self.zoom_original.connect('clicked', self.__zoom_original_cb)
        toolbar_box.toolbar.insert(self.zoom_original, -1)
        self.zoom_original.show()

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

        self._zoom_update_sensitive(self.original_zlevel)

    def can_zoom_in(self, cfont_size):
        limit = self.original_zlevel + Pango.SCALE * 4
        return cfont_size < limit

    def can_zoom_out(self, cfont_size):
        limit = self.original_zlevel - Pango.SCALE * 4
        return cfont_size > limit

    def can_zoom_original(self, cfont_size):
        upper = self.original_zlevel + .5
        lower = self.original_zlevel - .5
        return cfont_size > upper or cfont_size < lower

    def _zoom_update_sensitive(self, cfont_size):
        self.zoom_in.set_sensitive(self.can_zoom_in(cfont_size))
        self.zoom_out.set_sensitive(self.can_zoom_out(cfont_size))
        self.zoom_original.set_sensitive(self.can_zoom_original(cfont_size))

    def __zoom_out_cb(self, button):
        window = self.client.get_widget().get_active()
        font_desc = window.get_pango_context().get_font_description()
        font_desc.set_size(font_desc.get_size() - Pango.SCALE)
        if button.is_sensitive():
            window.override_font(font_desc)
        self._zoom_update_sensitive(font_desc.get_size())

    def __zoom_in_cb(self, button):
        window = self.client.get_widget().get_active()
        font_desc = window.get_pango_context().get_font_description()
        font_desc.set_size(font_desc.get_size() + Pango.SCALE)
        if button.is_sensitive():
            window.override_font(font_desc)
        self._zoom_update_sensitive(font_desc.get_size())

    def __zoom_original_cb(self, button):
        window = self.client.get_widget().get_active()
        font_desc = window.get_pango_context().get_font_description()
        font_desc.set_size(self.original_zlevel)
        window.override_font(font_desc)
        self._zoom_update_sensitive(font_desc.get_size())

    def _toggled_theme(self, button):
        # previous_theme = self._theme_colors[self._theme_state]
        if self._theme_state == "dark":
            self._theme_state = "light"
        elif self._theme_state == "light":
            self._theme_state = "dark"
        else:
            self._theme_state = "light"
        self.update_theme()

    def update_theme(self):
        if self._theme_state == "light":
            self._theme_toggler.set_icon_name('dark-theme')
            self._theme_toggler.set_tooltip('Switch to Dark Theme')
        elif self._theme_state == "dark":
            self._theme_toggler.set_icon_name('light-theme')
            self._theme_toggler.set_tooltip('Switch to Light Theme')
        else:
            self._theme_toggler.set_icon_name('light-theme')
            self._theme_toggler.set_tooltip('Switch to Light Theme')

        for tab in range(self.client.get_widget().tabs.get_n_pages()):
            window = self.client.get_widget().tabs.get_nth_page(tab)
            fg_color = Gdk.RGBA()
            fg_color.parse(self._theme_colors[self._theme_state]['fg_color'])
            bg_color = Gdk.RGBA()
            bg_color.parse(self._theme_colors[self._theme_state]['bg_color'])
            window.override_background_color(Gtk.StateFlags.NORMAL, bg_color)
            window.override_color(Gtk.StateFlags.NORMAL, fg_color)

    def _get_data(self):
        data = {}
        data['nick'] = self.client.core.window.network.me
        data['server'] = self.client.core.window.network.server
        data['username'] = self.client.core.window.network.server
        data['fullname'] = self.client.core.window.network.fullname
        data['password'] = self.client.core.window.network.password
        data['current-window'] = self.client.core.manager.get_active().id
        data['channels'] = []
        data['scrollback'] = {}

        for tab in range(self.client.get_widget().tabs.get_n_pages()):
            window = self.client.get_widget().tabs.get_nth_page(tab)
            font_desc = window.get_pango_context().get_font_description()
            data['font-size-{}'.format(self.no_of_tabs)] = font_desc.get_size()
            self.no_of_tabs += 1

        data['theme'] = self._theme_state
        data['num-of-tabs'] = self.no_of_tabs

        for i in range(self.client.core.manager.tabs.get_n_pages()):
            win = self.client.core.manager.tabs.get_nth_page(i)
            if win.id == "status":
                continue
            if win.is_channel():
                data['channels'].append(win.id)
            buf = win.output.get_buffer()
            data['scrollback'][win.id] = buf.get_text(buf.get_start_iter(),
                                                      buf.get_end_iter(), True)

        return data

    def _connection_cb(self, widget):
        connected = widget.get_active()
        if connected:
            widget.set_tooltip(_('Disconnect'))
            widget.set_icon_name('connect')
            self._load_data(self.data)
        else:
            widget.set_tooltip(_('Connect'))
            widget.set_icon_name('disconnect')
            self.client.run_command('quit Leaving...')
            self.data = self._get_data()

    def __visibility_notify_event_cb(self, window, event):
        self.is_visible = event.state != Gdk.VisibilityState.FULLY_OBSCURED

        # Configuracion por defecto

    def default_config(self):
        if os.path.exists(ETC_CONFIG_PATH):
            self.read_defaults_from_config(ETC_CONFIG_PATH)
        elif os.path.exists(DEFAULT_CONFIG_PATH):
            data = self.read_defaults_from_config(DEFAULT_CONFIG_PATH)
            if not "server" in data:
                self.client.join_server('irc.libera.chat')
            if not "channels" in data:
                self.i18n_channels()
        else:
            self.client.join_server('irc.libera.chat')
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
        config = configparser.ConfigParser()
        try:
            config.read_file(fp)
            fp.close()
        except Exception as error:
            logging.debug('Reading configuration, error: %s' % error)
            fp.close()
            return {"server": None, "channels": None}

        DATA = {"server": None, "channels": None}
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
        self._load_data(data)

    def _load_data(self, data):
        self.client.run_command('NICK %s' % (data['nick']))

        self.client.join_server(data['server'])
        for chan in data['channels']:
            self.client.add_channel(chan)
            self.client.add_channel_other(chan)
        self.client.core.window.network.requested_joins = set()
        for winid in list(data['scrollback'].keys()):
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

        num_of_tabs = data.get('num-of-tabs')
        for num in range(num_of_tabs):
            if 'font-size-{}'.format(num) in data.keys():
                window = self.client.get_widget().tabs.get_nth_page(num)
                font_size = data.get('font-size-{}'.format(num))
                pdesc = Pango.FontDescription.new()
                pdesc.set_size(font_size)
                window.override_font(pdesc)
        self._theme_state = data.get('theme')

        self.update_theme()

    def write_file(self, file_path):
        if not self.metadata['mime_type']:
            self.metadata['mime_type'] = 'text/plain'

        data = self._get_data()
        fd = open(file_path, 'w')
        text = json.dumps(data)
        fd.write(text)
        fd.close()

