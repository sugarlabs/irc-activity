import logging
import os

import dbus

from sugar3.activity import activity

session_bus = dbus.SessionBus()

notifications_object = session_bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
notifications_interface = dbus.Interface(notifications_object, 'org.freedesktop.Notifications')

_notification_id = 0

def onText(e):
    activity_instance = e.window.get_toplevel()
    if activity_instance.is_visible:
        return

    if e.network.me in e.text:
        global _notification_id
        icon_path = os.path.join(activity.get_bundle_path(), 'activity',
                                 'activity-ircchat.svg')
        _notification_id = notifications_interface.Notify('', _notification_id,
                '', '', '', [], {'x-sugar-icon-file-name': icon_path}, -1)

