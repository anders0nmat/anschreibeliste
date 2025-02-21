from django_eventstream import send_event
from django.dispatch import receiver
from .models import Transaction
from django.db.models.signals import post_save

@receiver(post_save, sender=Transaction)
def notify_clients(instance: Transaction, created: bool, **_):
	if not created:
		return
	
	data = {
		"id": instance.pk,
		"account": instance.account.pk,
		"account_name": instance.account.name,
		"balance": instance.account.current_balance,
		"is_liquid": instance.account.is_liquid,
		"amount": instance.amount,
		"reason": instance.reason,
	}
	# Reversal transaction
	if instance.related_transaction is not None:
		data["related"] = instance.related_transaction.pk
	
	# Associate transaction with request
	if instance.idempotency_key is not None:
		data["idempotency_key"] = instance.idempotency_key

	send_event("transaction", "create", data)

