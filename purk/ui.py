import sys 
import os
import thread

from gi.repository import GObject

__sys_path = list(sys.path)
from gi.repository import Gtk
from gi.repository import Gdk
sys.path = __sys_path

import widgets
import windows

# Running from same package dir
urkpath = os.path.dirname(__file__)

def path(filename=""):
    if filename:
        return os.path.join(urkpath, filename)
    else:
        return urkpath

# Priority Constants
PRIORITY_HIGH = GObject.PRIORITY_HIGH
PRIORITY_DEFAULT = GObject.PRIORITY_DEFAULT
PRIORITY_HIGH_IDLE = GObject.PRIORITY_HIGH_IDLE
PRIORITY_DEFAULT_IDLE = GObject.PRIORITY_DEFAULT_IDLE
PRIORITY_LOW = GObject.PRIORITY_LOW


def set_clipboard(text):
    Gtk.clipboard_get(Gdk.SELECTION_CLIPBOARD).set_text(text)
    Gtk.clipboard_get(Gdk.SELECTION_PRIMARY).set_text(text)

class Source(object):
    __slots__ = ['enabled']
    def __init__(self):
        self.enabled = True
    def unregister(self):
        self.enabled = False

class GtkSource(object):
    __slots__ = ['tag']
    def __init__(self, tag):
        self.tag = tag
    def unregister(self):
        GObject.source_remove(self.tag)

def register_idle(f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(GObject.idle_add(callback, priority=priority))

def register_timer(time, f, *args, **kwargs):
    priority = kwargs.pop("priority",PRIORITY_DEFAULT_IDLE)
    def callback():
        return f(*args, **kwargs)
    return GtkSource(GObject.timeout_add(time, callback, priority=priority))

def fork(cb, f, *args, **kwargs):
    is_stopped = Source()
    def thread_func():
        try:
            result, error = f(*args, **kwargs), None
        except Exception, e:
            result, error = None, e

        if is_stopped.enabled:
            def callback():           
                if is_stopped.enabled:
                    cb(result, error)

            GObject.idle_add(callback)

    thread.start_new_thread(thread_func, ())
    return is_stopped

set_style = widgets.set_style

def we_get_signal(*what):
    GObject.idle_add(windows.manager.exit)

def open_file(path):
    pass
