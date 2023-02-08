import re

version_re = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9a-zA-Z.-]+))?(?:\+([0-9a-zA-Z.-]+))?$')


class SemVersion:

    def __init__(self, *args):
        if not args:
            self.version: str = '0.0.0'
        elif len(args) == 1:
            self.version: str = args[0].strip()
        else:
            self.major: int = args[0] if args else ''
            self.minor: int = args[1] if len(args) > 1 else ''
            self.patch: int = args[2] if len(args) > 2 else ''
            self.prerelease: str = args[3].strip() if len(args) > 3 else None
            self.build: str = args[4].strip() if len(args) > 4 else None
            self.version = f'{self.major}.{self.minor}.{self.patch}'
            self.version += f'-{self.prerelease}' if self.prerelease else ''
            self.version += f'+{self.build}' if self.build else ''
        match = version_re.match(self.version)
        if not match:
            raise ValueError(f'Invalid version string: {self.version}')
        self.major, self.minor, self.patch, self.prerelease, self.build = match.groups()
        if has_leading_zero(self.major):
            raise ValueError(f'Invalid leading zero in major: {self.version}')
        if has_leading_zero(self.minor):
            raise ValueError(f'Invalid leading zero in minor: {self.version}')
        if has_leading_zero(self.patch):
            raise ValueError(f'Invalid leading zero in patch: {self.version}')

        self._cmp_precedence_key = self._build_precedence_key()
        self._sort_precedence_key = self._build_precedence_key()

    def __str__(self):
        return self.version

    def __hash__(self):
        return hash((self.major, self.minor, self.patch, self.prerelease, self.build))

    def next_major(self):
        return SemVersion(self.major + 1, 0, 0)

    def next_minor(self):
        return SemVersion(self.major, self.minor + 1, 0)

    def next_patch(self):
        return SemVersion(self.major, self.minor, self.patch + 1)

    def _build_precedence_key(self):

        prerelease_k = (MaxIdentifier(),)
        build_k = (MaxIdentifier(),)
        if self.prerelease:
            prerelease_k = tuple(NumericIdentifier(part) if part.isdigit()
                                 else AlphaIdentifier(part) for part in self.prerelease)
        if self.prerelease:
            build_k = tuple(NumericIdentifier(part) if part.isdigit()
                            else AlphaIdentifier(part) for part in self.build)

        return (self.major,
                self.minor,
                self.patch,
                prerelease_k,
                build_k)

    @property
    def precedence_key(self):
        return self._sort_precedence_key

    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        if self < other:
            return -1
        elif self > other:
            return 1
        elif self == other:
            return 0
        else:
            return NotImplemented

    def __eq__(self, other):
        return (
            (
                    self.major == other.major
                    and self.minor == other.minor
                    and self.patch == other.patch
                    and (self.prerelease or ()) == (other.prerelease or ())
                    and (self.build or ()) == (other.build or ())
            )
            if isinstance(other, self.__class__)
            else NotImplemented
        )

    def __ne__(self, other):
        return (
            tuple(self) != tuple(other)
            if isinstance(other, self.__class__)
            else NotImplemented
        )

    def __lt__(self, other):
        return (
            self._cmp_precedence_key < other._cmp_precedence_key
            if isinstance(other, self.__class__)
            else NotImplemented
        )

    def __le__(self, other):
        return (
            self._cmp_precedence_key <= other._cmp_precedence_key
            if isinstance(other, self.__class__)
            else NotImplemented
        )

    def __gt__(self, other):
        return (
            self._cmp_precedence_key > other._cmp_precedence_key
            if isinstance(other, self.__class__)
            else NotImplemented
        )

    def __ge__(self, other):
        return (
            self._cmp_precedence_key >= other._cmp_precedence_key
            if isinstance(other, self.__class__)
            else NotImplemented
        )


def has_leading_zero(value):
    return (value
            and value[0] == '0'
            and value.isdigit()
            and value != '0')


class MaxIdentifier(object):

    def __repr__(self):
        return 'MaxIdentifier()'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return True

    def __le__(self, other):
        return self <= other if isinstance(other, self.__class__) else False

    def __ge__(self, other) -> bool:
        return self >= other if isinstance(other, self.__class__) else True


class NumericIdentifier(object):
    __slots__ = ['value']

    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return 'NumericIdentifier(%r)' % self.value

    def __eq__(self, other):
        if isinstance(other, NumericIdentifier):
            return self.value == other.value
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, (MaxIdentifier, AlphaIdentifier)):
            return True
        elif isinstance(other, NumericIdentifier):
            return self.value < other.value
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (MaxIdentifier, AlphaIdentifier)):
            return False
        elif isinstance(other, NumericIdentifier):
            return self.value > other.value
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, (MaxIdentifier, AlphaIdentifier)):
            return True
        elif isinstance(other, NumericIdentifier):
            return self.value <= other.value
        else:
            return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, (MaxIdentifier, AlphaIdentifier)):
            return False
        elif isinstance(other, NumericIdentifier):
            return self.value >= other.value
        else:
            return NotImplemented


class AlphaIdentifier(object):
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value.encode('ascii')

    def __repr__(self):
        return 'AlphaIdentifier(%r)' % self.value

    def __eq__(self, other):
        if isinstance(other, AlphaIdentifier):
            return self.value == other.value
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, MaxIdentifier):
            return True
        elif isinstance(other, NumericIdentifier):
            return False
        elif isinstance(other, AlphaIdentifier):
            return self.value < other.value
        else:
            return NotImplemented
