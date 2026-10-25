"""Small widget helpers shared by the pages of ohmychadwm-tweak-tool."""

import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

import ott_chadwm  # noqa: E402

KEEP_SECONDS = 15


def section(title):
    """Return a bold section heading."""
    lbl = Gtk.Label(label=title, xalign=0)
    lbl.add_css_class("section-title")
    return lbl


def muted(text=""):
    """Return a wrapped, dimmed label."""
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.add_css_class("muted")
    lbl.set_wrap(True)
    return lbl


def warning(text=""):
    """Return a wrapped orange warning label."""
    lbl = muted(text)
    lbl.add_css_class("warning-text")
    return lbl


def session_note():
    """Return a warning that this part is for the ohmychadwm session, or None when the app runs in it."""
    if ott_chadwm.in_session():
        return None
    return warning("You are not in an Ohmychadwm session: this part is for your Ohmychadwm desktop. You see it at "
                   "your next Ohmychadwm login, not here.")


def row_label(text):
    """Return a left-aligned label for the first column of a settings grid."""
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.set_valign(Gtk.Align.CENTER)
    return lbl


def settings_grid():
    """Return the settings grid every page uses."""
    g = Gtk.Grid(column_spacing=12, row_spacing=10)
    g.set_margin_top(6)
    return g


def page_box():
    """Return the padded vertical box a page is built in."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{side}")(24)
    return box


def status_label():
    """Return the orange status line shown at the bottom of a page."""
    lbl = Gtk.Label(label="", xalign=0)
    lbl.add_css_class("status-line")
    lbl.set_wrap(True)
    lbl.set_hexpand(True)
    return lbl


def set_status(label, text, error=False):
    """Show text in a status label, red when error."""
    label.set_text(text)
    if error:
        label.add_css_class("status-error")
    else:
        label.remove_css_class("status-error")


def clear(box):
    """Remove every child of box."""
    while (child := box.get_first_child()) is not None:
        box.remove(child)


def dropdown(names, current):
    """Return a searchable DropDown over names with current preselected (added when missing)."""
    names = list(names)
    if current and current not in names:
        names.insert(0, current)
    dd = Gtk.DropDown.new_from_strings(names)
    dd.set_enable_search(True)
    dd.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
    dd.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
    dd.set_hexpand(True)
    if current in names:
        dd.set_selected(names.index(current))
    return dd


def selected(dd):
    """Return the string selected in a string DropDown, or ''."""
    item = dd.get_selected_item()
    return item.get_string() if item else ""


def select(dd, value):
    """Select value in a string DropDown when it is there."""
    model = dd.get_model()
    for i in range(model.get_n_items()):
        if model.get_item(i).get_string() == value:
            dd.set_selected(i)
            return


def run_async(work, done):
    """Run work() in a daemon thread (xrandr, make, pkexec, …), then done(result) on the GTK thread."""

    def runner():
        result = work()
        GLib.idle_add(lambda: done(result) and False)

    threading.Thread(target=runner, daemon=True).start()


def ask_keep(parent, title, on_done):
    """Show a KEEP_SECONDS countdown dialog; on_done(True) on Keep, on_done(False) on Revert, close or timeout."""
    dlg = Gtk.Window(title="Keep this change?", transient_for=parent, modal=True)
    dlg.set_resizable(False)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)
    heading = Gtk.Label(xalign=0)
    heading.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
    countdown = muted()
    buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    buttons.set_halign(Gtk.Align.END)
    btn_revert = Gtk.Button(label="Revert")
    btn_keep = Gtk.Button(label="Keep")
    btn_keep.add_css_class("suggested-action")
    buttons.append(btn_revert)
    buttons.append(btn_keep)
    box.append(heading)
    box.append(countdown)
    box.append(buttons)
    dlg.set_child(box)

    left = [KEEP_SECONDS]
    decided = [False]

    def finish(keep):
        # Keep, Revert, close and the timer can all fire: only the first one counts.
        if decided[0]:
            return
        decided[0] = True
        GLib.source_remove(timer)
        dlg.destroy()
        on_done(keep)

    def tick():
        left[0] -= 1
        if left[0] <= 0:
            finish(False)
            return False
        countdown.set_label(f"Going back in {left[0]} seconds.")
        return True

    countdown.set_label(f"Going back in {left[0]} seconds.")
    timer = GLib.timeout_add_seconds(1, tick)
    btn_keep.connect("clicked", lambda _w: finish(True))
    btn_revert.connect("clicked", lambda _w: finish(False))
    dlg.connect("close-request", lambda _w: finish(False) or True)
    dlg.present()
    btn_keep.grab_focus()
