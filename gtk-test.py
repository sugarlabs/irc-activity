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
import gtk
import purk

class XoIRC(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.connect('destroy', gtk.main_quit)

        self.set_title('XoIRC')
        self.set_size_request(800, 450)

        client = purk.Client()
        client.add_channel('#olpc-help')
        client.join_server('irc.freenode.net')
        client.show()
        widget = client.get_widget()
        self.add(widget)
        self.show_all()

if __name__ == "__main__":
    init = XoIRC()
    gtk.main()
