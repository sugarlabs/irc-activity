# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

import os
import logging
from gettext import gettext as _

import gtk
import dbus

from sugar.activity import activity
from sugar import env
import purk

class IRCActivity(activity.Activity):
			
    def write_file(self, file_path):
        print "DEBUG: executing write_file"
        
        print "=== nickname ==="
        self.metadata['nickname'] = self.client.core.window.network.me
        print "=== ======== ==="
        
        print "=== channels ==="
        self.metadata['channels'] = self.client.core.channels
        print "=== ======== ==="
        
        print "=== server ==="
        self.metadata['server'] = self.client.core.window.network.server
        print "=== ====== ==="
        
        print "DEBUG: done with write_file"


    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        print "DEBUG: start IRC Activity"
        logging.debug('Starting the XoIRC Activity')
        self.set_title(_('Xo IRC Activity'))

        self.add_events(gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.connect('visibility-notify-event',
                     self.__visibility_notify_event_cb)

        self.is_visible = False

        self.client = purk.Client()
        self.client.join_server('us.freenode.net')
        self.client.add_channel('#sugar')
        #self.client.add_channel('#lmms')
        self.client.show()
        widget = self.client.get_widget()

        # CANVAS
        self.set_canvas(widget)

        # TOOLBAR
        toolbox = activity.ActivityToolbox(self)

        # Remove the Share button, since this activity isn't shareable
        toolbar = toolbox.get_activity_toolbar()
        toolbar.remove(toolbar.share)

        self.set_toolbox(toolbox)
        self.show_all()
        
        print "DEBUG: running nickname command"
        
        self.client.run_command("/nick hellobv")
        
        print "DEBUG: adding channels"
        try:
            for channel in self.metadata['channels']:
                self.client.add_channel(channel)
        except:
            print "ERROR: cannot add channels"
        
        print "DEBUG: setting server"
        
        try:
            self.client.run_command("/server " + self.metadata['server'])
        except:
            print "ERROR: cannot set server"

    def __visibility_notify_event_cb(self, window, event):
        self.is_visible = event.state != gtk.gdk.VISIBILITY_FULLY_OBSCURED


