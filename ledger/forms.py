from typing import Any
from django.forms import ModelForm, Form, CharField, IntegerField, HiddenInput, ModelChoiceField, BooleanField
from django.utils.translation import gettext_lazy as _

from .models import Account, Product, Transaction
from .formfield import FixedPrecisionField

class CreateAccountForm(ModelForm):
    class Meta:
        model = Account
        fields = ['display_name', 'full_name', 'balance', 'credit', 'group', 'member', 'permanent', 'active']
    
    balance = FixedPrecisionField(label=_('Balance'), decimal_places=2, min_value=0, required=False)

class RestrictedCreateAccountForm(CreateAccountForm):
    class Meta(CreateAccountForm.Meta):
        exclude = ['group', 'member', 'permanent']

    def save(self, commit: bool = True) -> Any:
        self.instance.member = False
        return super().save(commit)

class EditAccountForm(ModelForm):
    class Meta:
        model = Account
        fields = ['display_name', 'full_name', 'credit', 'group', 'member', 'permanent', 'active']

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

