from dataclasses import dataclass
from enum import Enum
import re

class Version(Enum):
    """
    Specifies the involved regions in the transaction.
    """

    nonEWR = 1
    """
    Members of the european economic area (EEA) and non-EEA-countries.

    Requires a BIC
    """

    onlyEWR = 2
    """
    Members of the EEA only

    BIC is optional
    """

class CharSet(Enum):
    utf8 = 1
    iso8859_1 = 2
    iso8859_2 = 3
    iso8859_4 = 4
    iso8859_5 = 5
    iso8859_7 = 6
    iso8859_10 = 7
    iso8859_15 = 8

class InvoiceType(Enum):
    """
    Identification-code of the transaction-type
    """

    creditTransfer = 'SCT'
    """
    SEPA Credit Tansfer
    """

    instantTransfer = 'INST'
    """
    SEPA Instant Credit Transfer

    Not all banks may support this type yet,
    deadline for supporting:
    - Within EEA:
      - Receive transactions: 2025-01-09
      - Send transactions: 2025-10-09
    - Outside of EEA:
      - Receive transactions: 2027-01-09
      - Send transactions: 2027-07-09
    """

@dataclass
class EPCCode:
    name: str
    iban: str
    amount: str = ''
    invoiceText: str = ''
    invoiceRef: str = ''
    bic: str = ''

    invoiceType = InvoiceType.instantTransfer
    purposeCode: str = ''
    additionalInformation: str = ''
    
    version = Version.onlyEWR
    charSet = CharSet.utf8

    def __str__(self) -> str:
        if self.version == Version.nonEWR and not self.bic:
            raise ValueError('No BIC speicifed for non-EWR transaction')
        if len(self.name) > 70:
            raise ValueError('Name can not be longer than 70 characters')
        if self.amount and not re.match(r"EUR\d+\.\d{2}", self.amount):
            raise ValueError('Invalid amount string, expected string of pattern "EUR123.45"')
        if len(self.purposeCode) > 4:
            raise ValueError('purpose code can not be longer than 4 characters')
        if len(self.invoiceRef) > 25:
            raise ValueError('Invoice Ref can not be longer than 25 characters')
        if len(self.invoiceText) > 140:
            raise ValueError('Invoice Text can not be longer than 140 characters')
        if self.invoiceRef and self.invoiceText:
            raise ValueError('Cannot specify both invoice ref and invoice text')
        if len(self.additionalInformation) > 70:
            raise ValueError('Additional Information can not be longer than 70 characters')

        result = f"""\
BCD
{str(self.version.value).rjust(3, '0')}
{self.charSet.value}
{self.invoiceType.value}
{self.bic}
{self.name}
{self.iban.replace(' ', '')}
{self.amount}
{self.purposeCode}
{self.invoiceRef}
{self.invoiceText}
{self.additionalInformation}"""
        return result.strip()

