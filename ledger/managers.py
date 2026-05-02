from django.db import models
from django.db.models import Window, F, Q
from django.db.models.functions import Lag, Lead
from django.db.models.functions.datetime import Now
from typing import TypeVar
from datetime import timedelta
from django.contrib.auth.models import User

class TransactionQuerySet(models.QuerySet):
    def annotate_revertible(self, user: User, revert_threshold: timedelta = None):
        """
        Annotates the queryset with `allow_revert`.
        
        This indicates whether `user` is allowed to revert a transaction, taking into account
        - Whether the transaction is already reverted
        - Whether the user is staff
        - Whether the transaction was issued by `user`
        - Whether the transaction was issued no more than `revert_threshold` ago
        """
        revert_threshold = revert_threshold or self.model.revert_threshold
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
        timejump = timejump or self.model.timejump_threshold
        return self.annotate(
            _previous_timestamp=Window(expression=Lag("timestamp", offset=1, default=None), order_by='timestamp'),
            _timedelta_before=F("timestamp") - F("_previous_timestamp"),
            timejump_before=Q(_timedelta_before__gt=timejump),

            _next_timestamp=Window(expression=Lead("timestamp", offset=1, default=Now()), order_by='timestamp'),
            _timedelta_after=F("_next_timestamp") - F("timestamp"),
            timejump_after=Q(_timedelta_after__gt=timejump),
        )

class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)\
            .filter(closing_balance=None)
    
    Self = TypeVar("Self")
    def annotate_revertible(self: Self, user: User, revert_threshold: timedelta = None) -> Self: ...
    def annotate_timejump(self: Self, timejump: timedelta = None) -> Self: ...

class ProductManager(models.Manager):
    def grouped(self):
        return self.filter(visible=True).order_by(F("group__order").asc(nulls_first=True), 'order').prefetch_related('group')

