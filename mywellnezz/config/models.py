"""Configuration models: what is persisted on disk (no secrets) and how."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mywellnezz.api.dto import Facility, User

# Legacy attribute names (v1 config) mapped to the current model, including the
# odd one-off ``mobile_phoneNumber`` used by the old UserContext.
_PROFILE_FIELDS: dict[str, tuple[str, ...]] = {
    'id': ('id',),
    'usr': ('usr', 'accountUsername'),
    'first_name': ('first_name', 'firstName'),
    'last_name': ('last_name', 'lastName'),
    'gender': ('gender',),
    'inclusive_gender': ('inclusive_gender', 'inclusiveGender'),
    'address1': ('address1',),
    'zip_code': ('zip_code', 'zipCode'),
    'city': ('city',),
    'state_province': ('state_province', 'stateProvince'),
    'email': ('email',),
    'phone_number': ('phone_number', 'phoneNumber'),
    'mobile_phone_number': ('mobile_phone_number', 'mobile_phoneNumber', 'mobilePhoneNumber'),
    'display_weight': ('display_weight', 'displayWeight'),
    'display_birth_date': ('display_birth_date', 'displayBirthDate'),
    'display_height': ('display_height', 'displayHeight'),
    'age': ('age',),
    'picture_url': ('picture_url', 'pictureUrl'),
    'modified_on': ('modified_on', 'modifiedOn'),
    'token_expire': ('token_expire',),
}


@dataclass
class UserProfile:
    """Persisted user profile. The password and the session token live in the OS vault."""

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
    token_expire: datetime | None = None
    facilities: list[Facility] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'UserProfile':
        profile = cls()
        for attr, names in _PROFILE_FIELDS.items():
            value = next((data.get(n) for n in names if data.get(n) is not None), None)
            if value is not None:
                setattr(profile, attr, value)
        profile.modified_on = _parse_datetime(profile.modified_on)
        profile.token_expire = _parse_datetime(profile.token_expire)
        profile.facilities = [
            f if isinstance(f, Facility) else Facility.from_payload(f)
            for f in (data.get('facilities') or [])
        ]
        return profile

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for attr in _PROFILE_FIELDS:
            value = getattr(self, attr)
            if value is not None:
                data[attr] = value.isoformat() if isinstance(value, datetime) else value
        if self.facilities:
            data['facilities'] = [_facility_dict(f) for f in self.facilities]
        return data

    def as_user(self, token: str | None = None) -> User:
        """Build the runtime user from the persisted profile (token not stored on disk)."""
        return User(
            id=self.id,
            usr=self.usr,
            first_name=self.first_name,
            last_name=self.last_name,
            gender=self.gender,
            inclusive_gender=self.inclusive_gender,
            address1=self.address1,
            zip_code=self.zip_code,
            city=self.city,
            state_province=self.state_province,
            email=self.email,
            phone_number=self.phone_number,
            mobile_phone_number=self.mobile_phone_number,
            display_weight=self.display_weight,
            display_birth_date=self.display_birth_date,
            display_height=self.display_height,
            age=self.age,
            picture_url=self.picture_url,
            modified_on=self.modified_on,
            token=token,
            token_expire=self.token_expire,
            facilities=list(self.facilities),
        )

    @classmethod
    def from_user(cls, user: User) -> 'UserProfile':
        """Persist the current state of a runtime user (password/token excluded)."""
        return cls(
            id=user.id,
            usr=user.usr,
            first_name=user.first_name,
            last_name=user.last_name,
            gender=user.gender,
            inclusive_gender=user.inclusive_gender,
            address1=user.address1,
            zip_code=user.zip_code,
            city=user.city,
            state_province=user.state_province,
            email=user.email,
            phone_number=user.phone_number,
            mobile_phone_number=user.mobile_phone_number,
            display_weight=user.display_weight,
            display_birth_date=user.display_birth_date,
            display_height=user.display_height,
            age=user.age,
            picture_url=user.picture_url,
            modified_on=user.modified_on,
            token_expire=user.token_expire,
            facilities=list(user.facilities),
        )


def _facility_dict(facility: Facility) -> dict[str, Any]:
    return {k: v for k, v in facility.__dict__.items() if v is not None}


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


@dataclass
class AppConfig:
    """Root configuration persisted as JSON."""

    user_choice: int | None = None
    facility_choice: int | None = None
    auto_book: bool = True
    users: list[UserProfile] = field(default_factory=list)

    def current_user(self) -> UserProfile:
        if self.user_choice is None or self.user_choice >= len(self.users):
            raise IndexError('No user selected')
        return self.users[self.user_choice]

    def set_user_choice(self, choice: int) -> None:
        if choice < len(self.users):
            self.user_choice = choice

    def set_facility_choice(self, choice: int) -> None:
        if self.user_choice is not None and choice < len(self.users[self.user_choice].facilities):
            self.facility_choice = choice

    def current_facility(self):
        user = self.current_user()
        if self.facility_choice is None or self.facility_choice >= len(user.facilities):
            raise IndexError('No facility selected')
        return user.facilities[self.facility_choice]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'AppConfig':
        return cls(
            user_choice=data.get('user_choice'),
            facility_choice=data.get('facility_choice'),
            auto_book=data.get('auto_book', True),
            users=[UserProfile.from_dict(u) for u in (data.get('users') or [])],
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.user_choice is not None:
            data['user_choice'] = self.user_choice
        if self.facility_choice is not None:
            data['facility_choice'] = self.facility_choice
        data['auto_book'] = self.auto_book
        data['users'] = [u.to_dict() for u in self.users]
        return data
