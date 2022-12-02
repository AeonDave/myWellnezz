from datetime import datetime, timedelta


class Booking:
    def __init__(self, l_start, **kwargs):
        self.available = kwargs.get('bookingAvailable')
        self.can_book: bool = False if not self.available or str(
            kwargs.get('bookingUserStatus')).lower() != 'canbook' else True
        if self.available:
            self.start: datetime = datetime.fromisoformat(kwargs.get('bookingOpensOn')).replace(tzinfo=None)
            self.end: datetime = l_start - timedelta(minutes=kwargs.get('cancellationMinutesInAdvance'))
