"""Data transfer objects for the MyWellness API.

Each DTO tolerates missing fields so a partial payload never crashes the app:
unusable objects (e.g. events without a date) are filtered out at parse time.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from dateutil import parser as date_parser


def _first(payload: dict[str, Any], *names: str, default: Any = None) -> Any:
    """Return the first non-None value among ``names``, supporting camelCase and snake_case."""
    for name in names:
        value = payload.get(name)
        if value is not None:
            return value
    return default


@dataclass
class Facility:
    id: str | None = None
    url: str | None = None
    name: str | None = None
    address: str | None = None
    website: str | None = None
    phone_number: str | None = None
    logo_url: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> 'Facility':
        return cls(
            id=payload.get('id'),
            url=payload.get('url'),
            name=payload.get('name'),
            address=payload.get('address'),
            website=payload.get('website'),
            phone_number=_first(payload, 'phoneNumber', 'phone_number'),
            logo_url=_first(payload, 'logoUrl', 'logo_url'),
        )


@dataclass
class User:
    """A logged-in user: profile fields plus the session token (never persisted to disk)."""

    id: str | None = None
    usr: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    inclusive_gender: str | None = None
    address1: str | None = None
    zip_code: str | None = None
    city: str | None = None
    state_province: str | None = None
    email: str | None = None
    phone_number: str | None = None
    mobile_phone_number: str | None = None
    display_weight: str | None = None
    display_birth_date: str | None = None
    display_height: str | None = None
    age: int | None = None
    picture_url: str | None = None
    modified_on: datetime | None = None
    token: str | None = None
    token_expire: datetime | None = None
    facilities: list[Facility] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> 'User':
        modified_on = _first(payload, 'modifiedOn', 'modified_on')
        return cls(
            id=payload.get('id'),
            usr=_first(payload, 'accountUsername', 'usr'),
            first_name=_first(payload, 'firstName', 'first_name'),
            last_name=_first(payload, 'lastName', 'last_name'),
            gender=payload.get('gender'),
            inclusive_gender=_first(payload, 'inclusiveGender', 'inclusive_gender'),
            address1=payload.get('address1'),
            zip_code=_first(payload, 'zipCode', 'zip_code'),
            city=payload.get('city'),
            state_province=_first(payload, 'stateProvince', 'state_province'),
            email=payload.get('email'),
            phone_number=_first(payload, 'phoneNumber', 'phone_number'),
            mobile_phone_number=_first(payload, 'mobilePhoneNumber', 'mobile_phone_number'),
            display_weight=_first(payload, 'displayWeight', 'display_weight'),
            display_birth_date=_first(payload, 'displayBirthDate', 'display_birth_date'),
            display_height=_first(payload, 'displayHeight', 'display_height'),
            age=payload.get('age'),
            picture_url=_first(payload, 'pictureUrl', 'picture_url'),
            modified_on=date_parser.parse(modified_on) if modified_on else None,
        )

    def set_token(self, token: str | None, expire_in: Any) -> None:
        """Store the bearer token and its lifetime in seconds."""
        self.token = token.strip() if token else None
        self.token_expire = (
            datetime.now() + timedelta(seconds=int(expire_in)) if expire_in is not None else None
        )


@dataclass
class Event:
    id: str | None = None
    name: str | None = None
    room: str | None = None
    start_hour: int | None = None
    start_minutes: int | None = None
    end_hour: int | None = None
    end_minutes: int | None = None
    partition_date: int | None = None
    assigned_to: str | None = None
    max_participants: int | None = None
    actual_participants: int | None = None
    booking_opens_on: datetime | None = None
    available_places: int | None = None
    booking_user_status: str | None = None
    booking_available: bool = False
    is_participant: bool = False
    is_in_waiting_list: bool = False
    uid: str = ''
    start: datetime | None = None
    end: datetime | None = None
    can_book: bool = False
    status: str = ''

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> 'Event | None':
        """Build an event from an API payload; ``None`` when the event has no usable date."""
        partition_date = payload.get('partitionDate')
        booking_opens_on = payload.get('bookingOpensOn')
        event = cls(
            id=payload.get('id'),
            name=payload.get('name'),
            room=payload.get('room'),
            start_hour=payload.get('startHour'),
            start_minutes=payload.get('startMinutes'),
            end_hour=payload.get('endHour'),
            end_minutes=payload.get('endMinutes'),
            partition_date=partition_date,
            assigned_to=payload.get('assignedTo'),
            max_participants=payload.get('maxParticipants'),
            actual_participants=payload.get('actualParticipants'),
            booking_opens_on=(
                date_parser.parse(booking_opens_on).replace(tzinfo=None)
                if booking_opens_on
                else datetime.now()
            ),
            available_places=payload.get('availablePlaces'),
            booking_user_status=payload.get('bookingUserStatus'),
            booking_available=bool(payload.get('bookingAvailable')),
            is_participant=bool(payload.get('isParticipant')),
            is_in_waiting_list=bool(payload.get('isInWaitingList')),
        )
        if event.partition_date is None:
            return None
        event.uid = sha256(f'{event.id}/{event.partition_date}'.encode()).hexdigest()
        event.start = date_parser.parse(
            f'{event.partition_date}T'
            f'{str(event.start_hour).zfill(2)}:{str(event.start_minutes).zfill(2)}:00'
        )
        event.end = date_parser.parse(
            f'{event.partition_date}T'
            f'{str(event.end_hour).zfill(2)}:{str(event.end_minutes).zfill(2)}:00'
        )
        event.can_book = event.booking_user_status == 'CanBook'
        event.status = event.get_status()
        return event

    def is_ended(self) -> bool:
        return self.end is not None and datetime.now() >= self.end

    def is_started(self) -> bool:
        return self.start is not None and datetime.now() >= self.start

    def is_bookable(self) -> bool:
        return (
            self.can_book
            and self.start is not None
            and self.start > datetime.now()
            and datetime.now() >= (self.booking_opens_on or datetime.min)
        )

    def get_status(self) -> str:
        if not self.booking_available:
            return 'Unshedulable'
        if self.is_in_waiting_list:
            return 'WaitingList'
        if self.is_participant:
            return 'Booked'
        if self.is_bookable():
            return 'Full' if self.available_places == 0 else 'Open'
        if self.is_started() and not self.is_ended():
            return 'Progress'
        return 'Ended' if self.is_ended() else 'Planned'
