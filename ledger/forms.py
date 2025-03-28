from time import time_ns
from django.forms import ModelForm, Form, CharField, IntegerField, HiddenInput, ModelChoiceField, ChoiceField

from .models import Account, Product
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

    credit = FixedPrecisionField(decimal_places=2)
    balance = FixedPrecisionField(decimal_places=2, disabled=True, initial=0)

class TransactionForm(Form):
    action = ChoiceField(choices={'deposit': 'Deposit', 'withdraw': 'Withdraw'}, widget=HiddenInput)
    account = ModelChoiceField(Account.objects.filter(active=True), widget=HiddenInput)
    amount = FixedPrecisionField(decimal_places=2, min_value=1)
    reason = CharField(required=False)
    
class ProductTransactionForm(Form):
    account = ModelChoiceField(Account.objects.filter(active=True))
    product = ModelChoiceField(Product.objects)
    amount = IntegerField(min_value=1, initial=1, required=False)
    
    

