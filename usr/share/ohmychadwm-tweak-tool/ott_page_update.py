"""Update & News page: updates waiting, Update now (in a terminal), Restart after a new kernel, and Kiro News.

Recovery (package keys, the problems of this boot) is ATT's ground (Erik, 2026-11-15): its Maintenance page has it.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import ott_i18n  # noqa: E402
import ott_update  # noqa: E402
import log  # noqa: E402
from ott_i18n import _, ngettext  # noqa: E402
from ott_widgets import muted, page_box, run_async, section, set_status, status_label  # noqa: E402


def _language():
    return (ott_i18n.ACTIVE or ott_i18n.SYSTEM or "en").split(".")[0]


class UpdatePage:
    """Keep the system up to date and read the Kiro News, in plain words."""

    def __init__(self):
        box = page_box()

        box.append(section(_("Updates")))
        self._updates_note = muted(_("Looking for updates…"))
        box.append(self._updates_note)
        self._updates_list = muted()
        self._updates_list.set_selectable(True)
        self._updates_list.set_visible(False)
        box.append(self._updates_list)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._btn_update = Gtk.Button(label=_("Update now"))
        self._btn_update.add_css_class("suggested-action")
        self._btn_update.set_tooltip_text(_("Opens a terminal: you see every step and type your password there."))
        self._btn_update.connect("clicked", lambda _widget: self._terminal(ott_update.UPDATE))
        btn_check = Gtk.Button(label=_("Look again"))
        btn_check.connect("clicked", lambda _widget: self.load())
        self._btn_restart = Gtk.Button(label=_("Restart now"))
        self._btn_restart.add_css_class("destructive-action")
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", lambda _widget: ott_update.reboot())
        for widget in (self._btn_update, btn_check, self._btn_restart):
            row.append(widget)
        box.append(row)
        self._restart_note = muted(_("A new kernel is installed. Restart to use it; until then some devices may not "
                                     "work."))
        self._restart_note.add_css_class("warn")
        self._restart_note.set_visible(False)
        box.append(self._restart_note)
        self._status = status_label()
        box.append(self._status)

        box.append(section(_("Kiro News")))
        self._news = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(self._news)

        self.widget = box
        self.load()

    def load(self):
        """Look for updates and read the news."""
        self._updates_note.set_label(_("Looking for updates…"))

        def work():
            return ott_update.pending(), ott_update.restart_needed(), ott_update.news(_language())

        run_async(work, self._loaded)

    def _loaded(self, result):
        updates, restart, news = result
        if updates is None:
            self._updates_note.set_label(_("Could not reach the package mirrors. Check the internet connection."))
            self._updates_list.set_visible(False)
        elif not updates:
            self._updates_note.set_label(_("Everything is up to date."))
            self._updates_list.set_visible(False)
        else:
            self._updates_note.set_label(ngettext("{n} update is waiting.", "{n} updates are waiting.",
                                                  len(updates)).format(n=len(updates)))
            shown = updates[:25]
            more = len(updates) - len(shown)
            text = "\n".join(shown) + (("\n" + _("… and {n} more.").format(n=more)) if more else "")
            self._updates_list.set_label(text)
            self._updates_list.set_visible(True)
        self._btn_restart.set_visible(restart)
        self._restart_note.set_visible(restart)

        while (child := self._news.get_first_child()) is not None:
            self._news.remove(child)
        for item in news:
            entry = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            title = Gtk.Label(label=f"{item['date']}  {item['title']}", xalign=0, wrap=True)
            title.add_css_class("heading")
            entry.append(title)
            text = item["text"]
            entry.append(muted(text if len(text) < 300 else text[:297].rsplit(" ", 1)[0] + "…"))
            if item["url"]:
                link = Gtk.LinkButton(uri=item["url"], label=_("Read more"))
                link.set_halign(Gtk.Align.START)
                entry.append(link)
            self._news.append(entry)
        if not news:
            self._news.append(muted(_("No news yet.")))

    def _terminal(self, command):
        log.log_info(f"terminal: {command}")
        ok, msg = ott_update.terminal(command)
        if ok:
            set_status(self._status, _("A terminal window opened. Look again when it is done."))
        else:
            set_status(self._status, msg, error=True)

