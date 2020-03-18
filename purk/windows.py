from gi.repository import Gtk
from gi.repository import Gdk

from .conf import conf
from . import widgets
from . import irc

def append(window, manager):
    print("** DEBUG :: Add Window: ", window)
    manager.add(window)


def append(window1, manager):
    print("** DEBUG :: Add window1: ", window1)
    manager.add(window1)


def remove(window, manager):
    print("** DEBUG :: Remove Window: ", window)
    manager.remove(window)

    # i don't want to have to call this
    window.destroy()


def new(wclass, network, id, core):
    if network is None:
        network = irc.dummy_network

    w = get(wclass, network, id, core)
    if not w:
        w = wclass(network, id, core)
        append(w, core.manager)

    return w


def get(windowclass, network, id, core):
    if network:
        id = network.norm_case(id)

    for w in core.manager:
        if (type(w).__name__,
            w.network,
            w.id) == (windowclass.__name__,
                      network,
                      id):
            return w


def get_with(manager, wclass=None, network=None, id=None):
    if network and id:
        id = network.norm_case(id)

    for w in list(manager):
        for to_find, found in (
                (wclass, type(w)), (network, w.network), (id, w.id)):
            # to_find might be False but not None (if it's a DummyNetwork)
            if to_find is not None and to_find != found:
                break
        else:
            yield w


def get_default(network, manager):
    window = manager.get_active()

    if window.network == network:
        return window

    # There can be only one...
    for window in get_with(manager, None, network):
        return window


class Window(Gtk.VBox):
    need_vbox_init = True

    def transfer_text(self, _widget, event):
        if event.string and not self.input.is_focus():
            self.input.grab_focus()
            self.input.set_position(-1)
            self.input.event(event)

    def write(self, text, activity_type=None, line_ending='\n', fg=None):
        if activity_type is None:
            activity_type = widgets.EVENT
        if self.manager.get_active() != self:
            self.activity = activity_type
        self.output.write(text, line_ending, fg)

    def get_id(self):
        if self.network:
            return self.network.norm_case(self.rawid)
        else:
            return self.rawid

    def set_id(self, id):
        self.rawid = id
        self.update()

    id = property(get_id, set_id)

    def get_toplevel_title(self):
        return self.rawid

    def get_title(self):
        return self.rawid

    def get_activity(self):
        return self.__activity

    def set_activity(self, value):
        if value:
            self.__activity.add(value)
        else:
            self.__activity = set()
        self.update()

    activity = property(get_activity, set_activity)

    def focus(self):
        pass

    def activate(self):
        self.manager.set_active(self)
        self.focus()

    def close(self, *args):
        self.events.trigger("Close", window=self)
        remove(self, self.manager)

    def update(self):
        self.manager.update(self)

    def __init__(self, network, id, core):
        self.manager = core.manager
        self.events = core.events

        if self.need_vbox_init:
            # make sure we don't call this an extra time when mutating
            Gtk.VBox.__init__(self, False)
            self.need_vbox_init = False

        if hasattr(self, "buffer"):
            self.output = widgets.TextOutput(core, self, self.buffer)
        else:
            self.output = widgets.TextOutput(core, self)
            self.buffer = self.output.get_buffer()

        if hasattr(self, "input"):
            if self.input.parent:
                self.input.parent.remove(self.input)
        else:
            self.input = widgets.TextInput(self, core)

        self.network = network
        self.rawid = id

        self.__activity = set()

    def is_query(self):
        return False

    def is_channel(self):
        return False


class SimpleWindow(Window):

    def __init__(self, network, id, core):
        Window.__init__(self, network, id)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        self.pack_end(self.input, False, True, 0)

        topbox = Gtk.ScrolledWindow()
        topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        topbox.add(self.output)

        self.pack_end(topbox, True, True, 0)

        self.show_all()


class StatusWindow(Window):

    def get_toplevel_title(self):
        return '%s - %s' % (self.network.me, self.get_title())

    def get_title(self):
        # Something about self.network.isupport
        if self.network.status:
            return "%s" % self.network.server
        else:
            return "[%s]" % self.network.server

    def __init__(self, network, id, core):
        Window.__init__(self, network, id, core)

        self.nick_label = widgets.NickEditor(self, core)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)
        self.manager = core.manager
        botbox = Gtk.HBox()
        botbox.add(self.input)
        botbox.pack_end(self.nick_label, False, True, 0)

        self.pack_end(botbox, False, True, 0)

        topbox = Gtk.ScrolledWindow()
        topbox.set_vexpand(True)
        topbox.add(self.output)

        self.pack_end(topbox, True, True, 0)

        self.show_all()


class QueryWindow(Window):

    def __init__(self, network, id, core):
        Window.__init__(self, network, id, core)

        self.nick_label = widgets.NickEditor(self, core)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        botbox = Gtk.HBox()
        botbox.add(self.input)
        botbox.pack_end(self.nick_label, False, True, 0)

        self.pack_end(botbox, False, True, 0)

        topbox = Gtk.ScrolledWindow()
        topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        topbox.add(self.output)

        self.pack_end(topbox, True, True, 0)

        self.show_all()

    def is_query(self):
        return True


def move_nicklist(paned, event):
    paned._moving = (
        event.type == Gdk.EventType._2BUTTON_PRESS,
        paned.get_position()
    )


def drop_nicklist(paned, event):
    width = paned.get_allocated_width()
    pos = paned.get_position()

    double_click, nicklist_pos = paned._moving

    if double_click:
        # if we're "hidden", then we want to unhide
        if width - pos <= 10:
            # get the normal nicklist width
            conf_nicklist = conf.get("ui-gtk/nicklist-width", 200)

            # if the normal nicklist width is "hidden", then ignore it
            if conf_nicklist <= 10:
                paned.set_position(width - 200)
            else:
                paned.set_position(width - conf_nicklist)

        # else we hide
        else:
            paned.set_position(width)

    else:
        if pos != nicklist_pos:
            conf["ui-gtk/nicklist-width"] = width - pos - 6


class ChannelWindow(Window):

    def __init__(self, network, id, core):
        Window.__init__(self, network, id, core)
        print("** DEBUG :: NEW Channel Window: ", network, ", ", id, ", ", core)

        self.nicklist = widgets.Nicklist(self, core)
        self.nick_label = widgets.NickEditor(self, core)

        self.focus = self.input.grab_focus
        self.connect("key-press-event", self.transfer_text)

        topbox = Gtk.ScrolledWindow()
        topbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        topbox.add(self.output)

        nlbox = Gtk.ScrolledWindow()
        nlbox.set_size_request(conf.get("ui-gtk/nicklist-width", 112), -1)
        nlbox.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nlbox.add(self.nicklist)

        botbox = Gtk.HBox()
        botbox.add(self.input)
        botbox.pack_end(self.nick_label, False, True, 0)

        self.pack_end(botbox, False, True, 0)

        pane = Gtk.HPaned()
        pane.pack1(topbox, resize=True, shrink=False)
        pane.pack2(nlbox, resize=False, shrink=True)

        self.nicklist.pos = None

        pane.connect("button-press-event", move_nicklist)
        pane.connect("button-release-event", drop_nicklist)

        self.pack_end(pane, True, True, 0)
        self.show_all()

    def is_channel(self):
        return True

    def is_channel_other(self):
        return True
