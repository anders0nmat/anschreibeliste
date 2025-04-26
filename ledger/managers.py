from django.db import models
from django.db.models import Window, F, Q
from django.db.models.functions import Lag, Lead
from django.db.models.functions.datetime import Now
from typing import Optional, Union
from datetime import timedelta
from django.contrib.auth.models import User

class TransactionQuerySet(models.QuerySet):
    revert_threshold = timedelta(hours=12)
    timejump = timedelta(hours=6)

    def annotate_revertible(self, user: User, revert_threshold: timedelta = None):
        """
        Annotates the queryset with `allow_revert`.
        
        This indicates whether `user` is allowed to revert a transaction, taking into account
        - Whether the transaction is already reverted
        - Whether the user is staff
        - Whether the transaction was issued by `user`
        - Whether the transaction was issued no more than `revert_threshold` ago
        """
        revert_threshold = revert_threshold or self.revert_threshold
        if user.is_staff:
            return self.annotate(allow_revert=Q(related_transaction=None))
        elif revert_threshold is None:
            return self.annotate(allow_revert=Q(related_transaction=None) & Q(issuer=user))
        else:
            return self.annotate(
                _timedelta_now=Now() - F('timestamp'),
                allow_revert=Q(related_transaction=None) & Q(issuer=user) & Q(_timedelta_now__lt=revert_threshold))
        
    def annotate_timejump(self, timejump: timedelta = None):
        """
        Annotates the queryset with `timejump_before` and `timejump_after`.
        
        Indicating whether `timejump` lies between this transaction and
        - the next one (`timejump_after`)
        - the one before (`timejump_before`)
        """
        timejump = timejump or self.timejump
        return self.annotate(
            _previous_timestamp=Window(expression=Lag("timestamp", offset=1, default=None), order_by='timestamp'),
            _timedelta_before=F("timestamp") - F("_previous_timestamp"),
            timejump_before=Q(_timedelta_before__gt=timejump),

            _next_timestamp=Window(expression=Lead("timestamp", offset=1, default=Now()), order_by='timestamp'),
            _timedelta_after=F("_next_timestamp") - F("timestamp"),
            timejump_after=Q(_timedelta_after__gt=timejump),
        )

class TransactionManager(models.Manager):
    def __init__(self, timejump_threshold: Union[timedelta, False]=False, revert_threshold: Optional[timedelta] = None) -> None:
        super().__init__()
        self.default_timejump = timejump_threshold
        self.revert_threshold = revert_threshold

    def recent(self, account=None, timejump: Union[timedelta, False, None]=None, user: Optional[User] = None):
        """
        Returns a manager with regular properties applied:

        a) filtered for the specified account (all if not specified)
        b) annotated if the given time has passed between transactions (no annotations if False, default_timedelta is used if None).
           These can be accessed by the `timejump_before` and `timejump_after` fields on the resulting objects,
        c) annotated whether the specified user is allowed to revert the transaction (no annotations if None).
           This can be accessed by the `allow_revert` field on the resulting objects
           This is decided in order on the following questions:
           1. Is the current transaction already reverted? if yes => not allowed
           2. Is the specified user staff? if yes => allowed
           3. Is the specified user the issuer of the transaction? if no => not allowed
           4. Is the transaction less than the defined revert_timedelta in the past? if yes => allowed
           5. => not allowed
        """
        manager = self.filter(closing_balance=None).order_by('-timestamp')
        if account is not None:
            manager = manager.filter(account=account)

        if timejump is None:
            timejump = self.default_timejump
        if timejump is not False:
            manager = manager.annotate(
                _previous_timestamp=Window(expression=Lag("timestamp", offset=1, default=None), order_by='timestamp'),
                _timedelta_before=F("timestamp") - F("_previous_timestamp"),
                timejump_before=Q(_timedelta_before__gt=timejump),

                _next_timestamp=Window(expression=Lead("timestamp", offset=1, default=Now()), order_by='timestamp'),
                _timedelta_after=F("_next_timestamp") - F("timestamp"),
                timejump_after=Q(_timedelta_after__gt=timejump),
            )

        if user is not None:
            if user.is_staff:
                manager = manager.annotate(
                    allow_revert=Q(related_transaction=None))
            elif self.revert_threshold is None:
                manager = manager.annotate(
                    allow_revert=Q(related_transaction=None) & Q(issuer=user))
            else:
                manager = manager.annotate(
                    _timedelta_now=Now() - F('timestamp'),
                    allow_revert=Q(related_transaction=None) & Q(issuer=user) & Q(_timedelta_now__lt=self.revert_threshold))
            
        return manager.select_related('account')



class ProductManager(models.Manager):
    def grouped(self):
        return self.filter(visible=True).order_by(F("group__order").asc(nulls_first=True), 'order').prefetch_related('group')
    
