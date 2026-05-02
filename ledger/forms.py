from typing import Any, Callable, Iterator, Tuple
from django.forms import ModelForm, Form, CharField, IntegerField, HiddenInput, ModelChoiceField, BooleanField, ModelMultipleChoiceField, MultipleChoiceField, DateField
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from django.forms.widgets import TextInput, NumberInput, CheckboxSelectMultiple

from itertools import groupby

from .models import Account, Product, Transaction
from .formfield import FixedPrecisionField, DecimalInput, NativeDateInput

class GroupedModelChoiceIterator(ModelChoiceField.iterator):
    def __iter__(self) -> Iterator[Tuple[int | str, str]]:
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        for group, choices in groupby(
            self.queryset.all(),
            key=lambda row: getattr(row, self.field.group_by_field)
        ):
            if group is not None:
                yield (
                    self.field.group_label(group),
                    [self.choice(ch) for ch in choices]
                )

class GroupedModelChoiceField(ModelMultipleChoiceField):
    iterator = GroupedModelChoiceIterator

    def __init__(self, *args, group_by_field: str, group_label: str | Callable[[Any], str]=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.group_by_field = group_by_field
        if group_label is None:
            self.group_label = lambda x: x
        elif isinstance(group_label, str):
            self.group_label = lambda x: getattr(x, group_label)
        else:
            self.group_label = group_label

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
        help_texts = {
            'full_name': _("Optional. Used in the transaction qr-code."),
        }
    
    balance = FixedPrecisionField(label=_('Balance'), decimal_places=2, min_value=0, required=False)

class RestrictedCreateAccountForm(CreateAccountForm):
    class Meta(CreateAccountForm.Meta):
        exclude = ['group', 'member', 'permanent']

    def save(self, commit: bool = True) -> Any:
        self.instance.member = False
        return super().save(commit)

@default_placeholder
class EditAccountForm(CreateAccountForm):
    class Meta(CreateAccountForm.Meta):
        exclude = ['balance']
    balance = None

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

class TransactionListFilter(Form):
    account = GroupedModelChoiceField(Account.objects.all(), label=_('Account'), required=False, widget=CheckboxSelectMultiple, group_by_field="group", group_label="name")
    type = MultipleChoiceField(choices=Transaction.TransactionType.choices, label=pgettext_lazy('transaction', 'Type'), required=False, widget=CheckboxSelectMultiple)
    start = DateField(required=False, widget=NativeDateInput, label=_('Start'))
    end = DateField(required=False, widget=NativeDateInput, label=_('End'))
    hide_reverted = BooleanField(label=_('Hide reverted transactions'), required=False)