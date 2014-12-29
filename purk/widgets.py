import codecs

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from conf import conf
import parse_mirc


# Window activity Constants
HILIT = 'h'
TEXT = 't'
EVENT = 'e'
CURRENT = 'c'

ACTIVITY_MARKUP = {
    HILIT: "<span style='italic' foreground='#00F'>%s</span>",
    TEXT: "<span foreground='#ca0000'>%s</span>",
    EVENT: "<span foreground='#363'>%s</span>",
    CURRENT: "<span foreground='#000000'>%s</span>",
}

# This holds all tags for all windows ever
tag_table = Gtk.TextTagTable()

link_tag = Gtk.TextTag.new('link')
link_tag.set_property('underline', Pango.Underline.SINGLE)

indent_tag = Gtk.TextTag.new('indent')
indent_tag.set_property('indent', -20)

tag_table.add(link_tag)
tag_table.add(indent_tag)

# FIXME: MEH hates dictionaries, they remind him of the bad words
styles = {}


def style_me(widget, style):
    widget.set_style(styles.get(style))


def set_style(widget_name, style):
    if style:
        # FIXME: find a better way...
        dummy = Gtk.Label()
        dummy.set_style(None)

        def apply_style_fg(value):
            dummy.modify_text(Gtk.StateType.NORMAL, Gdk.color.parse(value))

        def apply_style_bg(value):
            dummy.modify_base(Gtk.StateType.NORMAL, Gdk.color.parse(value))

        def apply_style_font(value):
            dummy.modify_font(Pango.FontDescription(value))

        style_functions = (
            ('fg', apply_style_fg),
            ('bg', apply_style_bg),
            ('font', apply_style_font),
        )

        for name, f in style_functions:
            if name in style:
                f(style[name])

        style = dummy.rc_get_style()
    else:
        style = None

    styles[widget_name] = style


def menu_from_list(alist):
    while alist and not alist[-1]:
        alist.pop(-1)

    last = None
    for item in alist:
        if item != last:
            if item:
                if len(item) == 2:
                    name, function = item

                    menuitem = Gtk.ImageMenuItem(name)

                elif len(item) == 3:
                    name, stock_id, function = item

                    if isinstance(stock_id, bool):
                        menuitem = Gtk.CheckMenuItem(name)
                        menuitem.set_active(stock_id)
                    else:
                        menuitem = Gtk.ImageMenuItem(stock_id)

                if isinstance(function, list):
                    submenu = Gtk.Menu()
                    for subitem in menu_from_list(function):
                        submenu.append(subitem)
                    menuitem.set_submenu(submenu)

                else:
                    menuitem.connect("activate", lambda a, f: f(), function)

                yield menuitem

            else:
                yield Gtk.SeparatorMenuItem()

        last = item


class Nicklist(Gtk.TreeView):

    def click(self, widget, event):
        if event.button == 3:
            x, y = event.get_coords()

            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))

            c_data = self.events.data(
                window=self.win,
                data=self[data],
                menu=[])

            self.events.trigger("ListRightClick", c_data)

            if c_data.menu:
                menu = Gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)

        elif event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            x, y = event.get_coords()

            (data,), path, x, y = self.get_path_at_pos(int(x), int(y))

            self.events.trigger(
                "ListDoubleClick",
                window=self.win,
                target=self[data])

    def __getitem__(self, pos):
        return self.get_model()[pos][0]

    def __setitem__(self, pos, name_markup):
        realname, markedupname, sortkey = name_markup

        self.get_model()[pos] = realname, markedupname, sortkey

    def __len__(self):
        return len(self.get_model())

    def index(self, item):
        for i, x in enumerate(self):
            if x == item:
                return i

        return -1

    def append(self, realname, markedupname, sortkey):
        self.get_model().append((realname, markedupname, sortkey))

    def insert(self, pos, realname, markedupname, sortkey):
        self.get_model().insert(pos, (realname, markedupname, sortkey))

    def replace(self, names):
        self.set_model(Gtk.ListStore(str, str, str))

        column = Gtk.TreeViewColumn('', Gtk.CellRendererText(), text=1)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.append_column(column)

        for name in names:
            self.append(*name)

        self.get_model().set_sort_column_id(2, Gtk.SortType.ASCENDING)

    def remove(self, realname):
        index = self.index(realname)

        if index == -1:
            raise ValueError

        self.get_model().remove(self.get_model().iter_nth_child(None, index))

    def clear(self):
        self.get_model().clear()

    def __iter__(self):
        return (r[0] for r in self.get_model())

    def __init__(self, window, core):
        self.win = window
        self.core = core
        self.events = core.events

        Gtk.TreeView.__init__(self)

        self.replace(())

        self.set_headers_visible(False)
        self.set_property("fixed-height-mode", True)
        self.connect("button-press-event", self.click)
        self.connect_after("button-release-event", lambda *a: True)

        style_me(self, "nicklist")

# Label used to display/edit your current nick on a network


class NickEditor(Gtk.EventBox):

    def nick_change(self, entry):
        oldnick, newnick = self.label.get_text(), entry.get_text()

        if newnick and newnick != oldnick:
            self.events.run('nick %s' % newnick, self.win, self.win.network)

        self.win.input.grab_focus()

    def update(self, nick=None):
        self.label.set_text(nick or self.win.network.me)

    def to_edit_mode(self, widget, event):
        if self.label not in self.get_children():
            return

        if getattr(event, 'button', None) == 3:
            c_data = self.events.data(window=self.win, menu=[])
            self.events.trigger("NickEditMenu", c_data)

            if c_data.menu:
                menu = Gtk.Menu()
                for item in menu_from_list(c_data.menu):
                    menu.append(item)
                menu.show_all()
                menu.popup(None, None, None, event.button, event.time)

        else:
            entry = Gtk.Entry()
            entry.set_text(self.label.get_text())
            entry.connect('activate', self.nick_change)
            entry.connect('focus-out-event', self.to_show_mode)

            self.remove(self.label)
            self.add(entry)
            self.get_window().set_cursor(None)

            entry.show()
            entry.grab_focus()

    def to_show_mode(self, widget, event):
        self.remove(widget)
        self.add(self.label)
        self.win.input.grab_focus()
        self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.XTERM))

    def __init__(self, window, core):
        Gtk.EventBox.__init__(self)
        self.events = core.events
        self.win = window

        self.label = Gtk.Label()
        self.label.set_padding(5, 0)
        self.add(self.label)

        self.connect("button-press-event", self.to_edit_mode)

        self.update()

        self.connect(
            "realize",
            lambda *
            a: self.get_window().set_cursor(
                Gdk.Cursor(
                    Gdk.CursorType.XTERM)))

# The entry which you type in to send messages


class TextInput(Gtk.Entry):
    # Generates an input event

    def entered_text(self, ctrl):
        for line in self.text.splitlines():
            if line:
                e_data = self.events.data(
                    window=self.win, network=self.win.network,
                    text=line, ctrl=ctrl
                )
                self.events.trigger('Input', e_data)
                if not e_data.done:
                    self.events.run(line, self.win, self.win.network)

        self.text = ''

    def _set_selection(self, s):
        if s:
            self.select_region(*s)
        else:
            self.select_region(self.cursor, self.cursor)

    # some nice toys for the scriptors
    text = property(Gtk.Entry.get_text, Gtk.Entry.set_text)
    cursor = property(Gtk.Entry.get_position, Gtk.Entry.set_position)
    selection = property(Gtk.Entry.get_selection_bounds, _set_selection)

    def insert(self, text):
        self.do_insert_at_cursor(self, text)

    # hack to stop it selecting the text when we focus
    def do_grab_focus(self):
        temp = self.text, (self.selection or (self.cursor,) * 2)
        self.text = ''
        Gtk.Entry.do_grab_focus(self)
        self.text, self.selection = temp

    def keypress(self, event):
        keychar = (
            (Gdk.ModifierType.CONTROL_MASK, '^'),
            (Gdk.ModifierType.SHIFT_MASK, '+'),
            (Gdk.ModifierType.MOD1_MASK, '!')
        )

        key = ''
        for keymod, char in keychar:
            # we make this an int, because otherwise it leaks
            if int(event.state) & keymod:
                key += char
        key += Gdk.keyval_name(event.keyval)

        self.events.trigger(
            'KeyPress',
            key=key,
            string=event.string,
            window=self.win)

        if key == "^Return":
            self.entered_text(True)

        up = Gdk.keyval_from_name("Up")
        down = Gdk.keyval_from_name("Down")
        tab = Gdk.keyval_from_name("Tab")

        return event.keyval in (up, down, tab)

    def __init__(self, window, core):
        Gtk.Entry.__init__(self)
        self.events = core.events
        self.core = core
        self.win = window

        # we don't want key events to propogate so we stop them in
        # connect_after
        self.connect('key-press-event', TextInput.keypress)
        self.connect_after('key-press-event', lambda *a: True)

        self.connect('activate', TextInput.entered_text, False)

GObject.type_register(TextInput)


def prop_to_Gtk(textview, xxx_todo_changeme):
    (prop, val) = xxx_todo_changeme
    if val == parse_mirc.BOLD:
        val = Pango.Weight.BOLD

    elif val == parse_mirc.UNDERLINE:
        val = Pango.Underline.SINGLE

    return {prop: val}


def word_from_pos(text, pos):
    if text[pos] == ' ':
        return ' ', pos, pos + 1

    else:
        fr = text[:pos].split(" ")[-1]
        to = text[pos:].split(" ")[0]

        return fr + to, pos - len(fr), pos + len(to)


def get_iter_at_coords(view, x, y):
    return view.get_iter_at_location(
        *view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, int(x), int(y))
    )


def get_event_at_iter(view, iter, core):
    buffer = view.get_buffer()

    line_strt = buffer.get_iter_at_line(iter.get_line())
    line_end = line_strt.copy()
    line_end.forward_lines(1)

    pos = iter.get_line_offset()

    # Caveat: text must be a unicode string, not utf-8 encoded; otherwise our
    # offsets will be off when we use anything outside 7-bit ascii
    # Gtk.TextIter.get_text returns unicode but Gtk.TextBuffer.get_text does
    # not
    text = line_strt.get_text(line_end).rstrip("\n")

    word, fr, to = word_from_pos(text, pos)

    return core.events.data(
        window=view.win, pos=pos, text=text,
        target=word, target_fr=fr, target_to=to,
    )


class TextOutput(Gtk.TextView):

    def copy(self):
        startend = self.get_buffer().get_selection_bounds()

        tagsandtext = []
        if startend:
            start, end = startend

            while not start.equal(end):
                tags_at_iter = {}
                for tag in start.get_tags():
                    try:
                        tagname, tagval = eval(tag.get_property('name'))
                        tags_at_iter[tagname] = tagval
                    except NameError:
                        continue

                tagsandtext.append((dict(tags_at_iter), start.get_char()))
                start.forward_char()

        text = parse_mirc.unparse_mirc(tagsandtext)

        Gtk.clipboard_get(Gdk.SELECTION_CLIPBOARD).set_text(text)
        Gtk.clipboard_get(Gdk.SELECTION_PRIMARY).set_text(text)

        return text

    def clear(self):
        self.get_buffer().set_text('')

    def get_y(self):
        rect = self.get_visible_rect()
        return rect.y

    def set_y(self, y):
        iter = self.get_iter_at_location(0, y)
        if self.get_iter_location(iter).y < y:
            self.forward_display_line(iter)
        yalign = float(self.get_iter_location(iter).y - y) / self.height
        self.scroll_to_iter(iter, 0, True, 0, yalign)

        self.check_autoscroll()

    def get_ymax(self):
        buffer = self.get_buffer()
        return sum(self.get_line_yrange(buffer.get_end_iter())) - self.height

    def get_height(self):
        return self.get_visible_rect().height

    y = property(get_y, set_y)
    ymax = property(get_ymax)
    height = property(get_height)

    # the unknowing print weird things to our text widget function
    def write(self, text, line_ending='\n', fg=None):
        if not isinstance(text, unicode):
            try:
                text = codecs.utf_8_decode(text)[0]
            except:
                text = codecs.latin_1_decode(text)[0]
        tags, text = parse_mirc.parse_mirc(text)

        if fg:
            tags.append(
                {
                    'data': (
                        "foreground",
                        isinstance(
                            fg,
                            basestring) and (
                            '#%s' %
                            fg) or parse_mirc.get_mirc_color(fg)),
                    'from': 0,
                    'to': len(text)})

        buffer = self.get_buffer()

        cc = buffer.get_char_count()

        for tag in tags:
            tag_name = str(tag['data'])

            if not tag_table.lookup(tag_name):
                buffer.create_tag(tag_name, **prop_to_Gtk(self, tag['data']))

            buffer.apply_tag_by_name(
                tag_name,
                buffer.get_iter_at_offset(tag['from'] + cc),
                buffer.get_iter_at_offset(tag['to'] + cc)
            )

        buffer.insert_with_tags(
            buffer.get_end_iter(),
            text + line_ending,
            indent_tag
        )

    def popup(self, menu, event):
        hover_iter = get_iter_at_coords(self, *self.hover_coords)

        menuitems = []
        if not hover_iter.ends_line():
            c_data = get_event_at_iter(self, hover_iter)
            c_data.menu = []

            self.events.trigger("RightClick", c_data)

            menuitems = c_data.menu

        if not menuitems:
            c_data = self.events.data(menu=[])
            self.events.trigger("MainMenu", c_data)

            menuitems = c_data.menu

        for child in menu.get_children():
            menu.remove(child)

        for item in menu_from_list(menuitems):
            menu.append(item)

        menu.show_all()

    def mousedown(self, widget, event):
        if event.button == 3:
            self.hover_coords = event.get_coords()

    def mouseup(self, widget, event):
        if not self.get_buffer().get_selection_bounds():
            if event.button == 1:
                hover_iter = get_iter_at_coords(self, *self.hover_coords)

                if not hover_iter.ends_line():
                    c_data = get_event_at_iter(self, hover_iter, self.core)

                    self.events.trigger("Click", c_data)

            if self.is_focus():
                self.win.focus()

    def clear_hover(self, _widget=None, event=None):
        buffer = self.get_buffer()

        for fr, to in self.linking:
            buffer.remove_tag_by_name(
                "link",
                buffer.get_iter_at_mark(fr),
                buffer.get_iter_at_mark(to)
            )

        self.linking = set()
        self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)

    def hover(self, widget, event):
        if self.linking:
            self.clear_hover()

        hover_iter = get_iter_at_coords(self, *self.hover_coords)

        if not hover_iter.ends_line():
            h_data = get_event_at_iter(self, hover_iter, self.core)
            h_data.tolink = set()

            self.events.trigger("Hover", h_data)

            if h_data.tolink:
                buffer = self.get_buffer()

                offset = buffer.get_iter_at_line(
                    hover_iter.get_line()
                ).get_offset()

                for fr, to in h_data.tolink:
                    fr = buffer.get_iter_at_offset(offset + fr)
                    to = buffer.get_iter_at_offset(offset + to)

                    buffer.apply_tag_by_name("link", fr, to)

                    self.linking.add(
                        (buffer.create_mark(None, fr),
                            buffer.create_mark(None, to))
                    )

                    self.get_window(
                        Gtk.TextWindowType.TEXT
                    ).set_cursor(Gdk.Cursor(Gdk.HAND2))

        self.get_pointer()

    def scroll(self, widget, cairo_rect, _allocation=None):
        if self.autoscroll:
            def do_scroll():
                self.scroller.set_value(self.scroller.get_upper() -
                                        self.scroller.get_page_size())
                self._scrolling = False

            if not self._scrolling:
                self._scrolling = GObject.idle_add(do_scroll)

    def check_autoscroll(self, *args):
        def set_to_scroll():
            self.autoscroll = self.scroller.get_value() +      \
                self.scroller.get_page_size() >= \
                self.scroller.get_upper()

        GObject.idle_add(set_to_scroll)

    def __init__(self, core, window, buffer=None):
        if not buffer:
            buffer = Gtk.TextBuffer.new(tag_table)

        Gtk.TextView.__init__(self)
        self.set_buffer(buffer)
        self.core = core
        self.events = core.events
        self.win = window

        self.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.set_editable(False)
        self.set_cursor_visible(False)

        self.set_left_margin(3)
        self.set_right_margin(3)

        self.linking = set()

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self.connect('populate-popup', self.popup)
        self.connect('motion-notify-event', self.hover)
        self.connect('button-press-event', self.mousedown)
        self.connect('button-release-event', self.mouseup)
        self.connect_after('button-release-event', lambda *a: True)
        self.connect('leave-notify-event', self.clear_hover)

        self.hover_coords = 0, 0

        self.autoscroll = True
        self._scrolling = False
        self.scroller = Gtk.Adjustment()

        def setup_scroll(self, _adj, vadj):
            self.scroller = vadj

            if vadj:
                def set_scroll(adj):
                    self.autoscroll = adj.value + adj.page_size >= adj.upper

                vadj.connect("value-changed", set_scroll)
        # FIXME: set-scroll adjustment is no longer emitted.
        # Check http://developer.gnome.org/gtk3/3.3/ch25s02.html
        #self.connect("set-scroll-adjustments", setup_scroll)
        self.connect("size-allocate", self.scroll)

        def set_cursor(widget):
            self.get_window(Gtk.TextWindowType.TEXT).set_cursor(None)

        self.connect("realize", set_cursor)

        style_me(self, "view")


class WindowLabel(Gtk.EventBox):

    def update(self):
        title = self.win.get_title()

        for escapes in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')):
            title = title.replace(*escapes)

        for a_type in (HILIT, TEXT, EVENT, CURRENT):
            if a_type in self.win.activity:
                title = ACTIVITY_MARKUP[a_type] % title
                break

        self.label.set_markup(title)

    def tab_popup(self, event):
        if event.button == 3:  # right click
            c_data = self.events.data(window=self.win, menu=[])
            self.events.trigger("WindowMenu", c_data)

            c_data.menu += [
                None,
                ("Close", Gtk.STOCK_CLOSE, self.win.close),
            ]

            menu = Gtk.Menu()
            for item in menu_from_list(c_data.menu):
                menu.append(item)
            menu.show_all()
            menu.popup(None, None, None, event.button, event.time, None)

    def __init__(self, window, core):
        Gtk.EventBox.__init__(self)
        self.core = core
        self.events = core.events

        self.win = window
        self.connect("button-press-event", WindowLabel.tab_popup)

        self.label = Gtk.Label()
        self.add(self.label)

        self.update()
        self.show_all()


class FindBox(Gtk.HBox):

    def remove(self, *args):
        self.parent.remove(self)
        self.win.focus()

    def clicked(self, button, search_down=False):
        text = self.textbox.get_text()

        if not text:
            return

        buffer = self.win.output.get_buffer()

        if buffer.get_selection_bounds():
            if button == self.down:
                _, cursor_iter = buffer.get_selection_bounds()
            else:
                cursor_iter, _ = buffer.get_selection_bounds()
        else:
            cursor_iter = buffer.get_end_iter()

        if search_down:
            cursor = cursor_iter.forward_search(
                text, Gtk.TEXT_SEARCH_VISIBLE_ONLY
            )
        else:
            cursor = cursor_iter.backward_search(
                text, Gtk.TEXT_SEARCH_VISIBLE_ONLY
            )

        if not cursor:
            return

        fr, to = cursor

        if button == self.up:
            buffer.place_cursor(fr)
            self.win.output.scroll_to_iter(fr, 0)
        elif button == self.down:
            buffer.place_cursor(to)
            self.win.output.scroll_to_iter(to, 0)

        buffer.select_range(*cursor)

        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())

    def __init__(self, window):
        Gtk.HBox.__init__(self)

        self.win = window

        self.up = Gtk.Button(stock='Gtk-go-up')
        self.down = Gtk.Button(stock='Gtk-go-down')

        self.up.connect('clicked', self.clicked)
        self.down.connect('clicked', self.clicked, True)

        self.up.set_property('can_focus', False)
        self.down.set_property('can_focus', False)

        self.textbox = Gtk.Entry()

        self.textbox.connect('focus-out-event', self.remove)
        self.textbox.connect('activate', self.clicked)

        self.pack_start(Gtk.Label('Find:'), False, True, 0)
        self.pack_start(self.textbox, True, True, 0)

        self.pack_start(self.up, False, True, 0)
        self.pack_start(self.down, False, True, 0)

        self.show_all()


class UrkUITabs(Gtk.VBox):

    def __init__(self, core):
        Gtk.VBox.__init__(self)

        # threading stuff
        Gdk.threads_init()
        self.core = core
        self.events = core.events
        self.tabs = Notebook()
        self.tabs.set_property(
            "tab-pos",
            conf.get("ui-Gtk/tab-pos", Gtk.PositionType.BOTTOM)
        )

        self.tabs.set_scrollable(True)
        self.tabs.set_property("can-focus", False)
        self.pack_end(self.tabs, False, True, 0)

    def __iter__(self):
        return iter(self.tabs.get_children())

    def __len__(self):
        return self.tabs.get_n_pages()

    def exit(self, *args):
        self.events.trigger("Exit")

    def get_active(self):
        return self.tabs.get_nth_page(self.tabs.get_current_page())

    def set_active(self, window):
        self.tabs.set_current_page(self.tabs.page_num(window))

    def add(self, window):
        for pos in reversed(range(self.tabs.get_n_pages())):
            if self.tabs.get_nth_page(pos).network == window.network:
                break
        else:
            pos = self.tabs.get_n_pages() - 1

        self.tabs.insert_page(window, WindowLabel(window, self.core), pos + 1)

    def remove(self, window):
        self.tabs.remove_page(self.tabs.page_num(window))

    def update(self, window):
        self.tabs.get_tab_label(window).update()


class Notebook(Gtk.Notebook):

    def __init__(self):
        Gtk.Notebook.__init__(self)
        self.connect("switch-page", Notebook.switch_page, self)

    def switch_page(self, page, pnum, data):
        self.get_nth_page(pnum).activity = None
        self.get_nth_page(pnum).activity = CURRENT
