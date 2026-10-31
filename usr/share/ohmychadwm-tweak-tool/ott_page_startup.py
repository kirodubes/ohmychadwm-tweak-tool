"""Startup apps page: switch the run lines of ohmychadwm's run.sh on/off, add and remove your own."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import log  # noqa: E402
import ott_startup  # noqa: E402
from ott_widgets import clear, muted, page_box, section, session_note, set_status, status_label, warning  # noqa: E402
from ott_i18n import _  # noqa: E402

_COMPOSITORS = ("picom", "fastcompmgr", "xcompmgr", "compton")


class StartupPage:
    """One switch per run line; changes show at the next login."""

    def __init__(self):
        self.widget = page_box()
        self.refresh()

    def refresh(self):
        """Re-read run.sh and rebuild the list."""
        clear(self.widget)
        self.widget.append(section(_("Startup apps")))
        if (note := session_note()) is not None:
            self.widget.append(note)
        text = ott_startup.read()
        if not text:
            self.widget.append(muted(_("~/.config/ohmychadwm is not set up for this user — log into Ohmychadwm once "
                                     "first.")))
            return
        self.widget.append(muted(_("What Ohmychadwm starts when you log in (the run lines of "
                                 "~/.config/ohmychadwm/scripts/run.sh). Changes show at your next login.")))
        entries = ott_startup.entries(text)
        on_compositors = [e.command for e in entries if e.enabled and e.command.split()[0] in _COMPOSITORS]
        if len(on_compositors) > 1:
            self.widget.append(warning(_("More than one compositor is switched on — only one should run: {names}")
                                       .format(names=", ".join(c.split()[0] for c in on_compositors))))

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        for entry in entries:
            listbox.append(self._row(entry))
        self.widget.append(listbox)

        add = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._entry = Gtk.Entry(placeholder_text=_("Command to start at login, e.g. redshift-gtk"))
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_add)
        btn = Gtk.Button(label=_("Add"))
        btn.connect("clicked", self._on_add)
        add.append(self._entry)
        add.append(btn)
        self.widget.append(add)
        self._status = status_label()
        self.widget.append(self._status)

    def _row(self, entry):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(6)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text.set_hexpand(True)
        title = Gtk.Label(label=entry.note or entry.command.split()[0].rsplit("/", 1)[-1], xalign=0)
        text.append(title)
        text.append(muted(entry.command))
        box.append(text)
        if entry.added:
            remove = Gtk.Button(label=_("Remove"))
            remove.set_valign(Gtk.Align.CENTER)
            remove.connect("clicked", lambda _w, c=entry.command: self._change(ott_startup.remove, c))
            box.append(remove)
        switch = Gtk.Switch(active=entry.enabled)
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("state-set", lambda _w, state, e=entry: self._on_toggle(e, state))
        box.append(switch)
        return box

    def _on_toggle(self, entry, state):
        msg = (_("{command}: on from the next login.") if state
               else _("{command}: off from the next login.")).format(command=entry.command)
        if not state and any(name in entry.command for name in ott_startup.ESSENTIAL):
            msg += " " + _("Careful: Ohmychadwm needs {program} (bar status, password prompts or notifications).").format(
                program=entry.command.split()[0].rsplit("/", 1)[-1])
        self._write(ott_startup.set_enabled(ott_startup.read(), entry.command, state), msg, refresh=False)
        return False

    def _on_add(self, _widget):
        command = self._entry.get_text().strip()
        if command:
            self._change(ott_startup.add, command)

    def _change(self, transform, command):
        self._write(transform(ott_startup.read(), command), _("{command}: saved for the next login.").format(command=command))

    def _write(self, text, msg, refresh=True):
        try:
            ott_startup.write(text)
        except OSError as e:
            log.log_error(f"Startup apps: {e}")
            set_status(self._status, _("Could not write run.sh: {error}").format(error=e), error=True)
            return
        log.log_success(f"Startup apps: {msg}")
        if refresh:
            self.refresh()
        set_status(self._status, msg)
