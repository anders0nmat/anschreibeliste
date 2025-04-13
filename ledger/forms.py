from django.forms import ModelForm, Form, CharField, IntegerField, HiddenInput, ModelChoiceField, BooleanField
from django.utils.translation import gettext_lazy as _

from .models import Account, Product, Transaction
from .formfield import FixedPrecisionField

class AccountForm(ModelForm):
    label_suffix = ''
    
    class Meta:
        model = Account
        fields = ['name', 'balance', 'credit', 'group', 'member', 'permanent']

    def __init__(self, *args, **kwargs) -> None:
        instance: Account = kwargs.get('instance')
        initial: dict = kwargs.get('initial')
        if instance and initial is not None:
            initial.setdefault('balance', instance.current_balance)
        super().__init__(*args, **kwargs)

    balance = FixedPrecisionField(label=_('Balance'), decimal_places=2, disabled=True, initial=0)

class TransactionForm(Form):
    account = ModelChoiceField(Account.objects.filter(active=True), label=_('Account'), widget=HiddenInput)
    amount = FixedPrecisionField(label=_('Amount'), decimal_places=2, min_value=1)
    reason = CharField(label=_('Reason'), required=False)
    
class ProductTransactionForm(Form):
    account = ModelChoiceField(Account.objects.filter(active=True))
    product = ModelChoiceField(Product.objects)
    amount = IntegerField(min_value=1, initial=1, required=False)
    invert_member = BooleanField(initial=False, required=False)
    
class RevertTransactionForm(Form):
    transaction = ModelChoiceField(Transaction.objects) 

