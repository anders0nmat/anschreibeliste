from typing import Any
from django.forms import ModelForm, Form, CharField, IntegerField, HiddenInput, ModelChoiceField, BooleanField
from django.utils.translation import gettext_lazy as _
from django.forms.widgets import TextInput, NumberInput

from .models import Account, Product, Transaction
from .formfield import FixedPrecisionField, DecimalInput

def default_placeholder(cls=None, placeholder=" "):
    """
    Decorator for form classes.
    
    Sets the HTML-Attribute `placeholder` on widgets of type `TextInput`, `NumberInput` and `DecimalInput`
    """
    def _default_placeholder(cls):
        for field in cls.base_fields.values():
            if isinstance(field.widget, (TextInput, NumberInput, DecimalInput)): 
                field.widget.attrs.setdefault('placeholder', placeholder) 
        return cls
    if cls:
        return _default_placeholder(cls)
    return _default_placeholder
    
@default_placeholder
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

@default_placeholder
class EditAccountForm(ModelForm):
    class Meta:
        model = Account
        fields = ['display_name', 'full_name', 'credit', 'group', 'member', 'permanent', 'active']

@default_placeholder
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

