"""Compact Textual UI for account setup and gym-class booking."""

import asyncio
import re
from contextlib import suppress
from copy import copy
from datetime import datetime
from typing import ClassVar

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, ProgressBar, Static
from textual.worker import Worker, WorkerCancelled

from mywellnezz.api.dto import Event, Facility, User
from mywellnezz.app import constants, services
from mywellnezz.booking.engine import MyWellnezz
from mywellnezz.config import storage
from mywellnezz.config.models import AppConfig, UserProfile

EMAIL_RE = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

STATUS_STYLES = {
    'Planned': 'blue',
    'Unshedulable': 'red',
    'WaitingList': 'yellow',
    'Booked': 'green',
    'Booking': 'bold yellow',
    'Open': 'cyan',
    'Full': 'bold red',
    'Progress': 'green',
    'Ended': 'dim red',
}


def _plain(value: object | None, fallback: str = '—') -> str:
    return str(value) if value is not None and str(value) else fallback


def _time(value) -> str:
    return value.strftime('%a %d %b %H:%M') if value is not None else '—'


def _event_cells(event: Event) -> list[Text]:
    start = event.start.strftime('%a %d %b %H:%M') if event.start else '—'
    status = _plain(event.status, 'Unknown')
    free = _plain(event.available_places)
    return [
        Text(_plain(event.name)),
        Text(_plain(event.assigned_to)),
        Text(_plain(event.room)),
        Text(start),
        Text(free, style='red' if free == '0' else ''),
        Text(status, style=STATUS_STYLES.get(status, '')),
    ]


class AddUserModal(ModalScreen[User | None]):
    BINDINGS: ClassVar = [Binding('escape', 'cancel_modal', 'Cancel')]

    def compose(self) -> ComposeResult:
        yield Grid(
            Label('Add account', id='modal-title'),
            Input(placeholder='Email address', id='email'),
            Input(placeholder='Password', password=True, id='password'),
            Static('', id='feedback', markup=False),
            Horizontal(
                Button('Cancel', id='cancel'),
                Button('Sign in', variant='primary', id='login'),
            ),
            id='add-user-dialog',
        )

    def on_mount(self) -> None:
        self.query_one('#email', Input).focus()

    def action_cancel_modal(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#cancel')
    def cancel_button(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#login')
    @on(Input.Submitted)
    def submit(self) -> None:
        self.query_one('#login', Button).disabled = True
        self.query_one('#feedback', Static).update('Signing in…')
        self.run_worker(self._submit(), group='login', exclusive=True, exit_on_error=False)

    async def _submit(self) -> None:
        email = self.query_one('#email', Input)
        password = self.query_one('#password', Input)
        feedback = self.query_one('#feedback', Static)
        usr = email.value.replace(' ', '').strip()
        if not re.fullmatch(EMAIL_RE, usr):
            feedback.update('Enter a valid email address.')
            self.query_one('#login', Button).disabled = False
            return
        if not password.value:
            feedback.update('Enter a password.')
            self.query_one('#login', Button).disabled = False
            return
        try:
            user = await services.register_user(usr, password.value)
        except services.CredentialsRejected as ex:
            feedback.update(f'Invalid credentials: {ex}')
        except services.NetworkProblem as ex:
            feedback.update(f'Connection error: {ex}')
        except Exception as ex:  # noqa: BLE001 — keep service failures inside the UI
            feedback.update(f'Unable to sign in: {ex}')
        else:
            self.dismiss(user)
            return
        self.query_one('#login', Button).disabled = False


class PasswordModal(ModalScreen[str | None]):
    BINDINGS: ClassVar = [Binding('escape', 'cancel_modal', 'Cancel')]

    def __init__(self, usr: str):
        super().__init__()
        self._usr = usr

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(f'Password for {self._usr}', id='modal-title', markup=False),
            Input(placeholder='Password', password=True, id='password'),
            Horizontal(
                Button('Cancel', id='cancel'),
                Button('Sign in', variant='primary', id='login'),
            ),
            id='password-dialog',
        )

    def on_mount(self) -> None:
        self.query_one('#password', Input).focus()

    def action_cancel_modal(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#cancel')
    def cancel_button(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, '#login')
    @on(Input.Submitted)
    def submit(self) -> None:
        self.dismiss(self.query_one('#password', Input).value or None)


class ConfirmModal(ModalScreen[bool]):
    BINDINGS: ClassVar = [Binding('escape', 'cancel', 'Cancel')]

    def __init__(self, message: str, *, confirm_label: str = 'Yes'):
        super().__init__()
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self._message, id='modal-title', markup=False),
            Horizontal(
                Button('No', id='no'),
                Button(self._confirm_label, variant='error', id='yes'),
            ),
            id='confirm-dialog',
        )

    @on(Button.Pressed, '#no')
    def no(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, '#yes')
    def yes(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class MenuScreen(Screen):
    BINDINGS: ClassVar = [
        Binding('enter', 'open_account', 'Open'),
        Binding('a', 'add_account', 'Add'),
        Binding('d', 'remove_account', 'Remove'),
        Binding('q', 'quit_app', 'Quit'),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static('Accounts', id='menu-title')
        yield Static('No saved accounts. Choose Add to sign in.', id='menu-empty')
        yield DataTable(id='users')
        with Horizontal(id='menu-actions'):
            yield Button('Open', variant='primary', id='menu-open')
            yield Button('Add', id='menu-add')
            yield Button('Remove', id='menu-remove')
            yield Button('Quit', id='menu-quit')
        yield Static('', id='menu-status', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#users', DataTable)
        table.cursor_type = 'row'
        table.add_columns('Account', 'Gyms')
        self.reload()
        if self.app.config.users:
            selected = self.app.config.user_choice or 0
            table.move_cursor(row=min(selected, len(self.app.config.users) - 1))
        table.focus()

    def reload(self) -> None:
        table = self.query_one('#users', DataTable)
        table.clear()
        users = self.app.config.users
        for index, user in enumerate(users):
            table.add_row(Text(_plain(user.usr)), Text(str(len(user.facilities))), key=str(index))
        self.query_one('#menu-empty', Static).display = not users
        self.query_one('#users', DataTable).display = bool(users)
        self.query_one('#menu-open', Button).disabled = not users
        self.query_one('#menu-remove', Button).disabled = not users

    def _selected_index(self) -> int | None:
        table = self.query_one('#users', DataTable)
        row = table.cursor_row
        return row if 0 <= row < len(self.app.config.users) else None

    @on(Button.Pressed, '#menu-open')
    def open_button(self) -> None:
        self.action_open_account()

    @on(Button.Pressed, '#menu-add')
    def add_button(self) -> None:
        self.action_add_account()

    @on(Button.Pressed, '#menu-remove')
    def remove_button(self) -> None:
        self.action_remove_account()

    @on(Button.Pressed, '#menu-quit')
    def quit_button(self) -> None:
        self.action_quit_app()

    @on(DataTable.RowSelected, '#users')
    def user_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            index = int(event.row_key.value)
        except (TypeError, ValueError):
            return
        self._select_user(index)

    def action_open_account(self) -> None:
        index = self._selected_index()
        if index is not None:
            self._select_user(index)
        else:
            self._set_status('Select an account first.')

    def action_add_account(self) -> None:
        self.app.invalidate_navigation()
        self.query_one('#menu-open', Button).disabled = not self.app.config.users
        self._set_status('')
        self.app.push_screen(AddUserModal(), self._user_added)

    def action_remove_account(self) -> None:
        index = self._selected_index()
        if index is None:
            self._set_status('Select an account to remove.')
            return
        self.app.invalidate_navigation()
        self.query_one('#menu-open', Button).disabled = not self.app.config.users
        usr = self.app.config.users[index].usr or 'this account'
        self.app.push_screen(
            ConfirmModal(f'Remove {usr} and its saved credentials?'),
            lambda confirmed: self._delete_user(index, usr) if confirmed else None,
        )

    def action_quit_app(self) -> None:
        self.app.exit()

    def _set_status(self, message: str) -> None:
        self.query_one('#menu-status', Static).update(message)

    def _user_added(self, user: User | None) -> None:
        if user is None:
            return
        try:
            self.app.config = storage.add_user(self.app.config, UserProfile.from_user(user))
        except Exception as ex:  # noqa: BLE001 — include storage failures in feedback
            message = f'Cannot save account: {ex}'
            self._set_status(message)
            self.app.notify(escape(message), severity='error', title='Storage')
            return
        self.reload()
        self._set_status(f'Added {user.usr or "account"}.')

    def _delete_user(self, index: int, usr: str) -> None:
        try:
            self.app.config = storage.remove_user(self.app.config, index)
        except Exception as ex:  # noqa: BLE001 — include vault/config failures in feedback
            message = f'Cannot remove account: {ex}'
            self._set_status(message)
            self.app.notify(escape(message), severity='error', title='Storage')
            return
        self.reload()
        self._set_status(f'Removed {usr}.')

    def _select_user(self, index: int) -> None:
        if not 0 <= index < len(self.app.config.users):
            return
        self.app.invalidate_navigation()
        generation = self.app.navigation_generation
        origin = self.app.config.users[index].usr
        self.query_one('#menu-open', Button).disabled = True
        self.run_worker(
            self._load_account(index, origin, generation),
            group='account-selection', exclusive=True, exit_on_error=False
        )

    async def _load_account(self, index: int, origin: str | None, generation: int) -> None:
        if generation != self.app.navigation_generation:
            return
        self._set_status('Loading gyms…')
        try:
            await self.app.engine.reset()
            if (generation != self.app.navigation_generation
                    or index >= len(self.app.config.users)
                    or self.app.config.users[index].usr != origin):
                return
            self.app.config.set_user_choice(index)
            # Facility choices are per-account; the config stores only one global index.
            self.app.config.facility_choice = None
            profile = self.app.config.current_user()
            facilities = await services.ensure_facilities(
                self.app.config, profile, ask_password=self.app.ask_password
            )
            # A later Add/Remove/account selection owns navigation now. The service
            # commits only to its originating account; never redirect this result.
            if (generation != self.app.navigation_generation
                    or self.app.config.current_user().usr != origin):
                return
            profile = self.app.config.current_user()
            profile.facilities = list(facilities)
            self._save_config()
            if len(facilities) == 1:
                self.app.config.set_facility_choice(0)
                self._save_config()
                self.app.open_dashboard()
            else:
                await self.app.push_screen(GymScreen())
        except services.NoGyms:
            if generation == self.app.navigation_generation:
                self._set_status('This account is not registered at a gym.')
        except services.Cancelled:
            if generation == self.app.navigation_generation:
                self._set_status('Sign-in cancelled.')
        except (services.CredentialsRejected, services.NetworkProblem) as ex:
            if generation == self.app.navigation_generation:
                self._set_status(f'Login error: {ex}')
        except Exception as ex:  # noqa: BLE001 — contain service and engine failures
            if generation == self.app.navigation_generation:
                self._set_status(f'Unable to load gyms: {ex}')
        finally:
            if self.is_mounted and generation == self.app.navigation_generation:
                self.query_one('#menu-open', Button).disabled = not self.app.config.users

    def _save_config(self) -> None:
        try:
            storage.save_config(self.app.config)
        except Exception as ex:  # noqa: BLE001 — disk errors are user-visible
            message = f'Cannot save config: {ex}'
            self._set_status(message)
            self.app.notify(escape(message), severity='error', title='Storage')


class GymScreen(Screen):
    BINDINGS: ClassVar = [
        Binding('enter', 'open_gym', 'Open gym'),
        Binding('escape', 'back', 'Back'),
        Binding('q', 'quit_app', 'Quit'),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static('Select a gym', id='gym-title')
        yield Static('', id='gym-status', markup=False)
        yield DataTable(id='gyms')
        with Horizontal(id='gym-actions'):
            yield Button('Open gym', variant='primary', id='gym-open')
            yield Button('Back', id='gym-back')
            yield Button('Quit', id='gym-quit')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#gyms', DataTable)
        table.cursor_type = 'row'
        table.add_columns('Gym', 'Address')
        facilities = self.app.config.current_user().facilities
        for index, facility in enumerate(facilities):
            table.add_row(Text(_plain(facility.name)), Text(_plain(facility.address)), key=str(index))
        if facilities:
            selected = self.app.config.facility_choice or 0
            table.move_cursor(row=min(selected, len(facilities) - 1))
        else:
            self.query_one('#gym-status', Static).update('No gyms available for this account.')
            self.query_one('#gym-open', Button).disabled = True
        table.focus()

    @on(Button.Pressed, '#gym-open')
    def open_button(self) -> None:
        self.action_open_gym()

    @on(Button.Pressed, '#gym-back')
    def back_button(self) -> None:
        self.action_back()

    @on(Button.Pressed, '#gym-quit')
    def quit_button(self) -> None:
        self.action_quit_app()

    @on(DataTable.RowSelected, '#gyms')
    def gym_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_open_gym()

    def action_open_gym(self) -> None:
        table = self.query_one('#gyms', DataTable)
        index = table.cursor_row
        facilities = self.app.config.current_user().facilities
        if not 0 <= index < len(facilities):
            self.query_one('#gym-status', Static).update('Select a gym first.')
            return
        self.query_one('#gym-open', Button).disabled = True
        self.app.config.set_facility_choice(index)
        try:
            storage.save_config(self.app.config)
        except Exception as ex:  # noqa: BLE001 — report persistence errors, but retain chosen gym
            message = f'Cannot save gym choice: {ex}'
            self.query_one('#gym-status', Static).update(message)
            self.app.notify(escape(message), severity='error', title='Storage')
        self.app.open_dashboard()

    def action_back(self) -> None:
        self.app.invalidate_navigation()
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.invalidate_navigation()
        self.app.exit()


class DashboardScreen(Screen):
    BINDINGS: ClassVar = [
        Binding('b', 'book', 'Book / cancel queued action'),
        Binding('r', 'reload', 'Reload'),
        Binding('escape', 'back', 'Back'),
        Binding('q', 'quit_app', 'Quit'),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_events: dict[str, Event] = {}
        self._visible_uids: list[str] = []
        self._pending_uids: set[str] = set()
        self._refresh_worker: Worker | None = None
        self._operation_worker: Worker | None = None
        self._leave_worker: Worker | None = None
        self._timer: Timer | None = None
        self._refresh_busy = False
        self._operation_busy = False
        self._leaving = False
        self._elapsed = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static('', id='gym-summary', markup=False)
        yield Static('Loading classes…', id='dashboard-status', markup=False)
        yield Input(placeholder='Search classes by name, teacher or room', id='search')
        yield DataTable(id='events')
        yield Static('No class selected.', id='event-details', markup=False)
        with Horizontal(id='dashboard-actions'):
            yield Button('Book', variant='primary', id='book')
            yield Button('Reload', id='reload')
            yield Button('Back', id='back')
        yield ProgressBar(id='cycle-progress', show_eta=False, show_percentage=False)
        yield Static('', id='countdown', markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._update_summary()
        table = self.query_one('#events', DataTable)
        table.cursor_type = 'row'
        table.add_columns('Class', 'Teacher', 'Room', 'Starts', 'Free', 'Status')
        self._render_events({})
        self._timer = self.set_interval(1.0, self._on_tick)
        table.focus()
        self._start_refresh(force=True)

    async def on_unmount(self) -> None:
        await self._stop_refresh()

    def _update_summary(self) -> None:
        user = self.app.user
        facility = self.app.facility
        account = user.usr if user else 'Unknown account'
        name = ' '.join(part for part in (user.first_name, user.last_name) if part) if user else ''
        gym = facility.name if facility else 'Unknown gym'
        summary = f'{gym}  ·  {account}'
        if name:
            summary += f'  ·  {name}'
        if user and (user.display_height or user.display_weight):
            summary += f'  ·  {user.display_height or "?"} / {user.display_weight or "?"}'
        self.query_one('#gym-summary', Static).update(summary)

    def _selected_uid(self) -> str | None:
        table = self.query_one('#events', DataTable)
        row = table.cursor_row
        return self._visible_uids[row] if 0 <= row < len(self._visible_uids) else None

    def _render_events(self, events: dict[str, Event], preferred_uid: str | None = None) -> None:
        if preferred_uid is None:
            preferred_uid = self._selected_uid()
        self._all_events = dict(events)
        query = self.query_one('#search', Input).value.strip().casefold()
        visible = [
            (uid, event)
            for uid, event in self._all_events.items()
            if not query or query in ' '.join(
                _plain(value, '') for value in (event.name, event.assigned_to, event.room)
            ).casefold()
        ]
        table = self.query_one('#events', DataTable)
        table.clear()
        self._visible_uids = []
        for uid, event in visible:
            key = uid or event.uid
            table.add_row(*_event_cells(event), key=key)
            self._visible_uids.append(key)
        if self._visible_uids:
            selected = self._visible_uids.index(preferred_uid) if preferred_uid in self._visible_uids else 0
            table.move_cursor(row=selected)
        self._render_selected_event()
        self._sync_controls()

    @on(Input.Changed, '#search')
    def search_changed(self, event: Input.Changed) -> None:
        self._render_events(self._all_events)

    @on(DataTable.RowHighlighted, '#events')
    def event_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._render_selected_event()
        self._sync_controls()

    @on(DataTable.RowSelected, '#events')
    def event_selected(self, event: DataTable.RowSelected) -> None:
        self._render_selected_event()
        uid = event.row_key.value
        if uid in self._all_events:
            self._request_book(uid)

    @on(Button.Pressed, '#book')
    def book_button(self) -> None:
        self.action_book()

    @on(Button.Pressed, '#reload')
    def reload_button(self) -> None:
        self.action_reload()

    @on(Button.Pressed, '#back')
    def back_button(self) -> None:
        self.action_back()

    def _render_selected_event(self) -> None:
        uid = self._selected_uid()
        event = self._all_events.get(uid) if uid else None
        details = self.query_one('#event-details', Static)
        if event is None:
            query = self.query_one('#search', Input).value.strip()
            if self._all_events and query:
                details.update(f'No classes match “{query}”.')
            elif not self._all_events:
                details.update('No classes found for this gym.')
            else:
                details.update('No class selected.')
            return
        start = _time(event.start)
        end = event.end.strftime('%H:%M') if event.end is not None else '—'
        opening = _time(event.booking_opens_on)
        free = _plain(event.available_places)
        status = _plain(event.status, 'Unknown')
        details.update(
            f'{_plain(event.name)}\n'
            f'Teacher: {_plain(event.assigned_to)}  ·  Room: {_plain(event.room)}\n'
            f'Start: {start}  ·  End: {end}\n'
            f'Booking opens: {opening}  ·  Free: {free}  ·  Status: {status}'
        )

    def _active_task_uids(self, tasks: dict[str, object]) -> set[str]:
        active: set[str] = set()
        for uid, task in tasks.items():
            done = getattr(task, 'done', None)
            if not callable(done) or not done():
                active.add(uid)
        return active

    def _selected_event(self, uid: str | None = None) -> Event | None:
        return self._all_events.get(uid or self._selected_uid())

    def _action_label(self, event: Event | None) -> str:
        uid = event.uid if event else None
        if uid in self._pending_uids:
            return 'Cancel queued'
        if event is None:
            return 'Book'
        if event.is_participant:
            return 'Unbook'
        if event.is_in_waiting_list or event.available_places == 0 or (
            event.booking_opens_on is not None and event.booking_opens_on > datetime.now()
        ):
            return 'Book when available'
        return 'Book'

    def _can_queue(self, event: Event | None) -> bool:
        if event is None:
            return False
        if event.uid in self._pending_uids:
            return True
        if event.is_participant:
            return bool(
                event.start is not None
                and event.end is not None
                and event.start > datetime.now()
                and event.end > datetime.now()
                and not event.is_started()
            )
        return bool(
            event.booking_available
            and event.start is not None
            and event.end is not None
            and event.end > datetime.now()
            and not event.is_started()
        )

    def _sync_controls(self) -> None:
        if not self.is_mounted:
            return
        event = self._selected_event()
        busy = self._operation_busy or self._leaving
        book = self.query_one('#book', Button)
        book.label = self._action_label(event)
        book.disabled = busy or self._refresh_busy or not self._can_queue(event)
        self.query_one('#reload', Button).disabled = busy or self._refresh_busy
        self.query_one('#back', Button).disabled = busy
        self.query_one('#search', Input).disabled = busy
        self.query_one('#events', DataTable).disabled = busy

    def action_book(self) -> None:
        self._request_book(self._selected_uid())

    def _request_book(self, uid: str | None) -> None:
        if uid is None:
            self.query_one('#dashboard-status', Static).update('Select a class first.')
            return
        event = self._selected_event(uid)
        if event is None:
            self.query_one('#dashboard-status', Static).update('The selected class is no longer available.')
            return
        if self._operation_busy or self._refresh_busy or self._leaving:
            return
        if not self._can_queue(event):
            self.query_one('#dashboard-status', Static).update(
                'This class cannot be booked or has already started.'
            )
            return
        cancel_pending = uid in self._pending_uids
        if event.is_participant and not cancel_pending:
            self._leave_worker = self.run_worker(
                self._confirm_unbook(uid), group='confirm-booking', exclusive=True,
                exit_on_error=False,
            )
            return
        self._queue_booking(uid, expected_participation=event.is_participant,
                            cancel_pending=cancel_pending)

    async def _confirm_unbook(self, uid: str) -> None:
        event = self._selected_event(uid)
        if event is None:
            return
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f'Unbook {event.name or "this class"}?'),
        )
        if not confirmed:
            return
        try:
            current = await self.app.engine.get_event(uid)
        except KeyError:
            self.query_one('#dashboard-status', Static).update(
                'No unbooking queued: the class is no longer available.'
            )
            return
        if not current.is_participant:
            self.query_one('#dashboard-status', Static).update(
                'No unbooking queued: the class is no longer booked.'
            )
            return
        if current.start is None or current.end is None or current.is_started() or current.is_ended():
            self.query_one('#dashboard-status', Static).update(
                'No unbooking queued: the class has started or ended.'
            )
            return
        self._queue_booking(uid, expected_participation=True)

    def _queue_booking(
        self, uid: str, *, expected_participation: bool, cancel_pending: bool = False
    ) -> None:
        self._operation_busy = True
        self._sync_controls()
        self.query_one('#dashboard-status', Static).update('Submitting booking request…')
        self._operation_worker = self.run_worker(
            self._submit_booking(uid, expected_participation, cancel_pending),
            group='booking-operation', exclusive=True, exit_on_error=False,
        )

    async def _submit_booking(
        self, uid: str, expected_participation: bool, cancel_pending: bool
    ) -> None:
        action = 'unbook' if expected_participation else 'book'
        try:
            current = await self.app.engine.get_event(uid)
            if cancel_pending:
                tasks = await self.app.engine.get_book_tasks()
                task = tasks.get(uid)
                done = getattr(task, 'done', None)
                if task is None or (callable(done) and done()):
                    self._pending_uids.discard(uid)
                    self.query_one('#dashboard-status', Static).update(
                        'No queued action remains to cancel; no new action was started.'
                    )
                    return
            else:
                if current.is_participant != expected_participation:
                    message = (
                        'No unbooking queued: the class is no longer booked.'
                        if expected_participation
                        else 'No booking queued: the class is already booked.'
                    )
                    self.query_one('#dashboard-status', Static).update(message)
                    return
                if expected_participation and (
                    current.start is None or current.end is None
                    or current.is_started() or current.is_ended()
                ):
                    self.query_one('#dashboard-status', Static).update(
                        'No unbooking queued: the class has started or ended.'
                    )
                    return
            # The task gets an intent snapshot: a concurrent refresh can't turn unbook into book.
            result = await self.app.engine.set_book_task(
                self.app.user, self.app.facility, copy(current)
            )
            if result == 'queued':
                self._pending_uids.add(uid)
                self.query_one('#dashboard-status', Static).update(f'Queued to {action} {current.name or "class"}.')
            elif result == 'cancelled':
                self._pending_uids.discard(uid)
                self.query_one('#dashboard-status', Static).update(f'Cancelled queued action for {current.name or "class"}.')
            else:
                self.query_one('#dashboard-status', Static).update(
                    f'Not queued: {current.name or "class"} is not currently bookable.'
                )
            tasks = await self.app.engine.get_book_tasks()
            self._pending_uids = self._active_task_uids(tasks)
        except Exception as ex:  # noqa: BLE001 — surface engine failures without false success
            self.query_one('#dashboard-status', Static).update(f'Booking error: {ex}')
        finally:
            self._operation_busy = False
            self._sync_controls()

    def action_reload(self) -> None:
        if self._refresh_busy or self._operation_busy or self._leaving:
            return
        self._start_refresh(force=True)

    def _start_refresh(self, *, force: bool = False) -> None:
        if self._refresh_busy or (
            self._refresh_worker is not None and self._refresh_worker.is_running
        ):
            return
        self._refresh_busy = True
        self._sync_controls()
        self._refresh_worker = self.run_worker(
            self._refresh_once(force), group='dashboard-refresh', exclusive=False,
            exit_on_error=False,
        )

    async def _refresh_once(self, force: bool) -> None:
        self._refresh_busy = True
        self._sync_controls()
        if force:
            self.query_one('#dashboard-status', Static).update('Refreshing classes…')
        try:
            engine = self.app.engine
            clean_error: Exception | None = None
            try:
                await engine.clean_tasks()
            except Exception as ex:  # noqa: BLE001 — surface engine job errors, then continue sync
                # clean_tasks removes a failed job before surfacing its exception;
                # still consume events and the task table in this same tick.
                clean_error = ex
            events = await engine.get_events()
            should_refresh = force or engine.refresh_due(events)
            if should_refresh:
                self.query_one('#dashboard-status', Static).update('Refreshing classes…')
                events = await engine.update_events_event(
                    self.app.user, self.app.facility, self.app.config, events
                )
                self._elapsed = 0
            else:
                self._elapsed = max(int(engine.cycle_iteration) - 1, 0)
            tasks = await engine.get_book_tasks()
            self._pending_uids = self._active_task_uids(tasks)
            self._render_events(events)
            if clean_error is not None:
                self.query_one('#dashboard-status', Static).update(
                    f'Booking task failed: {clean_error}'
                )
            elif should_refresh:
                if events:
                    self.query_one('#dashboard-status', Static).update(f'{len(events)} classes loaded.')
                else:
                    self.query_one('#dashboard-status', Static).update('No classes found.')
        except asyncio.CancelledError:
            raise
        except Exception as ex:  # noqa: BLE001 — preserve prior rows and expose the failure
            self.query_one('#dashboard-status', Static).update(f'Refresh failed: {ex}')
        finally:
            self._refresh_busy = False
            self._sync_controls()
            self._update_countdown()

    def _on_tick(self) -> None:
        if self._leaving or self._operation_busy or self._refresh_busy:
            return
        self._start_refresh(force=False)

    def _update_countdown(self) -> None:
        timeout = max(int(self.app.engine.cycle_timeout), 1)
        remaining = max(timeout - self._elapsed, 0)
        self.query_one('#cycle-progress', ProgressBar).update(
            total=timeout, progress=min(self._elapsed, timeout)
        )
        self.query_one('#countdown', Static).update(
            f'Next refresh in {remaining}s  ·  b book/unbook  ·  r reload  ·  esc back  ·  q quit'
        )

    def action_back(self) -> None:
        self._request_leave(quit_app=False)

    def action_quit_app(self) -> None:
        self._request_leave(quit_app=True)

    def _request_leave(self, *, quit_app: bool) -> None:
        if self._leaving or self._operation_busy:
            return
        self._leaving = True
        self._sync_controls()
        # The exit worker belongs to the app so popping this screen cannot cancel itself.
        self._leave_worker = self.app.run_worker(
            self._leave_dashboard(quit_app), group='dashboard-exit', exclusive=True,
            exit_on_error=False,
        )

    async def _leave_dashboard(self, quit_app: bool) -> None:
        try:
            tasks = self._active_task_uids(await self.app.engine.get_book_tasks())
            if tasks:
                confirmed = await self.app.push_screen_wait(
                    ConfirmModal(
                        f'{len(tasks)} booking action(s) are queued. Leave and cancel them?',
                        confirm_label='Leave',
                    )
                )
                if not confirmed:
                    self._leaving = False
                    self.query_one('#dashboard-status', Static).update(
                        'Leaving cancelled; queued actions are still active.'
                    )
                    self._sync_controls()
                    return
            await self._stop_refresh()
            if quit_app:
                await self.app.engine.shutdown()
                self.app.exit()
            else:
                await self.app.engine.reset()
                if len(self.app.screen_stack) > 1:
                    await self.app.pop_screen()
                else:
                    await self.app.switch_screen(MenuScreen())
        except Exception as ex:  # noqa: BLE001 — prevent unsafe, silent context changes
            self.query_one('#dashboard-status', Static).update(f'Cannot leave dashboard: {ex}')
            self._leaving = False
            self._sync_controls()

    async def _stop_refresh(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        worker = self._refresh_worker
        self._refresh_worker = None
        if worker is not None and not worker.is_finished:
            worker.cancel()
            with suppress(WorkerCancelled):
                await worker.wait()


class MyWellnezzApp(App):
    TITLE = constants.name
    SUB_TITLE = f'v{constants.version}'
    CSS = """
    Screen { layout: vertical; }
    #menu-title, #gym-title { height: 1; padding: 0 1; text-style: bold; }
    #menu-empty { height: auto; padding: 1 2; color: $text-muted; }
    #users, #gyms { height: 1fr; min-height: 4; margin: 0 1; }
    #menu-actions, #gym-actions, #dashboard-actions {
        height: 3; align-horizontal: left; padding: 0 1;
    }
    #menu-actions Button, #gym-actions Button, #dashboard-actions Button { margin-right: 1; }
    #menu-status, #gym-status, #dashboard-status {
        height: 1; padding: 0 1; color: $text-muted; text-overflow: ellipsis;
    }
    #gym-summary { height: 1; padding: 0 1; text-style: bold; text-overflow: ellipsis; }
    #search { height: 3; margin: 0 1; }
    #events { height: 1fr; min-height: 4; margin: 0 1; }
    #event-details {
        height: 5; padding: 0 1; border-top: round $accent; text-overflow: ellipsis;
    }
    #cycle-progress { height: 1; margin: 0 1; }
    #countdown { height: 1; padding: 0 1; color: $text-muted; text-overflow: ellipsis; }
    #add-user-dialog, #password-dialog, #confirm-dialog {
        grid-size: 1; grid-gutter: 1 2; grid-rows: auto; padding: 1 2;
        width: 60; max-width: 90%; height: auto; border: heavy $accent; background: $surface;
    }
    #modal-title { text-style: bold; height: auto; }
    #feedback { height: auto; color: $error; }
    Horizontal { height: auto; align-horizontal: right; }
    Horizontal Button { margin-left: 1; }
    """

    def __init__(self, config: AppConfig, engine: MyWellnezz):
        super().__init__()
        self.config = config
        self.engine = engine
        self.user: User | None = None
        self.facility: Facility | None = None
        self._context_worker: Worker | None = None
        self.navigation_generation = 0

    def invalidate_navigation(self) -> None:
        """Retire pending screen transitions even if their I/O ignores cancellation."""
        self.navigation_generation += 1
        worker, self._context_worker = self._context_worker, None
        if worker is not None and not worker.is_finished:
            worker.cancel()

    def on_mount(self) -> None:
        self.push_screen(MenuScreen())

    async def on_shutdown(self) -> None:
        await self.engine.shutdown()

    async def ask_password(self, usr: str) -> str | None:
        return await self.push_screen_wait(PasswordModal(usr))

    def open_dashboard(self) -> None:
        if self._context_worker is not None and self._context_worker.is_running:
            return
        self._context_worker = self.run_worker(
            self._open_dashboard(self.navigation_generation),
            group='open-dashboard', exclusive=True, exit_on_error=False,
        )

    async def _open_dashboard(self, generation: int) -> None:
        try:
            if generation != self.navigation_generation:
                return
            origin = self.config.current_user().usr
            source_screen = self.screen
            # Snapshot the gym identity before login can replace or reorder profile memberships.
            selected_facility_id = self.config.current_facility().id
            if selected_facility_id is None:
                raise ValueError('The selected gym has no stable ID; choose it again from the menu.')
            await self.engine.reset()
            if (generation != self.navigation_generation
                    or self.config.current_user().usr != origin
                    or self.screen is not source_screen):
                return
            profile = self.config.current_user()
            user = await services.ensure_session(self.config, profile, ask_password=self.ask_password)
            if (generation != self.navigation_generation
                    or self.config.current_user().usr != origin
                    or self.screen is not source_screen):
                return
            profile = self.config.current_user()
            facility_index = next(
                (i for i, facility in enumerate(profile.facilities)
                 if facility.id == selected_facility_id),
                None,
            )
            if facility_index is None:
                raise ValueError(
                    'The selected gym is no longer available for this account. '
                    'Return to the menu and choose a gym again.'
                )
            facility = profile.facilities[facility_index]
            self.config.set_facility_choice(facility_index)
            try:
                storage.save_config(self.config)
            except Exception as ex:  # noqa: BLE001 — report but retain in-memory selection
                message = f'Cannot save gym choice: {ex}'
                self.notify(escape(message), severity='error', title='Storage')
                self._show_context_error(message)
            self.user = user
            self.facility = facility
            dashboard = DashboardScreen()
            if isinstance(self.screen, GymScreen):
                await self.switch_screen(dashboard)
            else:
                await self.push_screen(dashboard)
        except services.Cancelled:
            if generation == self.navigation_generation:
                self._show_context_error('Sign-in cancelled.')
        except (services.CredentialsRejected, services.NetworkProblem) as ex:
            if generation == self.navigation_generation:
                self._show_context_error(f'Login error: {ex}')
        except Exception as ex:  # noqa: BLE001 — surface engine/session errors in the active screen
            if generation == self.navigation_generation:
                self._show_context_error(f'Unable to open dashboard: {ex}')
        finally:
            if generation == self.navigation_generation and isinstance(self.screen, GymScreen):
                self.screen.query_one('#gym-open', Button).disabled = False

    def _show_context_error(self, message: str) -> None:
        self.notify(escape(message), severity='error', title='Account')
        screen = self.screen
        for selector in ('#gym-status', '#menu-status'):
            try:
                screen.query_one(selector, Static).update(message)
                return
            except NoMatches:
                continue
