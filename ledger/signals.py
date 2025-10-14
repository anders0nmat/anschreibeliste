from django.db.models.signals import post_save
from django.dispatch import receiver

from .eventstream import send_event
from .models import Transaction
from .utils.transaction import transaction_event

@receiver(post_save, sender=Transaction)
def notify_clients(instance: Transaction, created: bool, **_):
	if not created:
		return
	
	data = transaction_event(instance)

	send_event("transaction", "create", data, id=instance.pk)

