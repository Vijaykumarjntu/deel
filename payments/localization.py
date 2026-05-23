# payments/localization.py
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class CountryCode(Enum):
    INDIA = 'IN'
    BRAZIL = 'BR'
    GERMANY = 'DE'

@dataclass
class TaxRule:
    name: str
    rate: Decimal
    description: str
    applies_to: str  # 'contractor' or 'company'

@dataclass
class ComplianceRule:
    field_name: str
    label: str
    required: bool
    validation_pattern: Optional[str] = None
    example: Optional[str] = None

@dataclass
class PaymentMethod:
    code: str
    name: str
    available: bool
    processing_days: int
    fee_percentage: Decimal

@dataclass
class LegalRequirement:
    title: str
    description: str
    document_type: str
    required: bool

class LocalizationEngine:
    """Country-specific rules and compliance engine"""
    
    def __init__(self, country_code: str):
        self.country_code = country_code
        self.rules = self._load_country_rules()
    
    def _load_country_rules(self):
        """Load all country-specific rules"""
        rules = {
            'IN': {
                'name': 'India',
                'currency': 'INR',
                'currency_symbol': '₹',
                'language': 'en',
                'timezone': 'Asia/Kolkata',
                'tax_rules': [
                    TaxRule(
                        name='TDS',
                        rate=Decimal('0.10'),
                        description='Tax Deducted at Source (10%) for contractor payments',
                        applies_to='contractor'
                    ),
                    TaxRule(
                        name='GST',
                        rate=Decimal('0.18'),
                        description='Goods and Services Tax (18%)',
                        applies_to='company'
                    ),
                ],
                'compliance_rules': [
                    ComplianceRule(
                        field_name='pan',
                        label='PAN Card Number',
                        required=True,
                        # validation_pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                        validation_pattern=r'^[A-Za-z0-9]{10}$',
                        example='ABCDE1234F'
                    ),
                    ComplianceRule(
                        field_name='aadhar',
                        label='Aadhaar Number',
                        required=False,
                        validation_pattern=r'^[0-9]{12}$',
                        example='123456789012'
                    ),
                    ComplianceRule(
                        field_name='gstin',
                        label='GSTIN (if registered)',
                        required=False,
                        validation_pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                        example='22AAAAA0000A1Z'
                    ),
                ],
                'payment_methods': [
                    PaymentMethod('neft', 'NEFT', True, 1, Decimal('0.00')),
                    PaymentMethod('rtgs', 'RTGS', True, 0, Decimal('0.00')),
                    PaymentMethod('upi', 'UPI', True, 0, Decimal('0.00')),
                    PaymentMethod('imps', 'IMPS', True, 0, Decimal('0.005')),
                ],
                'legal_requirements': [
                    LegalRequirement(
                        title='ICDS Compliance',
                        description='Income Computation and Disclosure Standards',
                        document_type='declaration',
                        required=True
                    ),
                    LegalRequirement(
                        title='Form 15CA/CB',
                        description='Remittance to non-residents',
                        document_type='form',
                        required=False
                    ),
                ],
                'max_payment_per_month': Decimal('250000'),  # INR
                'contract_type': 'Independent Contractor Agreement',
                'notice_period_days': 30,
                'default_tax_withholding': True,
            },
            
            'BR': {
                'name': 'Brazil',
                'currency': 'BRL',
                'currency_symbol': 'R$',
                'language': 'pt',
                'timezone': 'America/Sao_Paulo',
                'tax_rules': [
                    TaxRule(
                        name='ISS',
                        rate=Decimal('0.05'),
                        description='Service Tax (ISS) - varies by city, standard 5%',
                        applies_to='contractor'
                    ),
                    TaxRule(
                        name='INSS',
                        rate=Decimal('0.11'),
                        description='Social Security (INSS) - 11%',
                        applies_to='contractor'
                    ),
                ],
                'compliance_rules': [
                    ComplianceRule(
                        field_name='cpf',
                        label='CPF Number',
                        required=True,
                        validation_pattern=r'^[0-9]{11}$',
                        example='12345678901'
                    ),
                    ComplianceRule(
                        field_name='rg',
                        label='RG (Identity Card)',
                        required=True,
                        validation_pattern=r'^[0-9]{9}$',
                        example='123456789'
                    ),
                    ComplianceRule(
                        field_name='pis_pasep',
                        label='PIS/PASEP',
                        required=False,
                        validation_pattern=r'^[0-9]{11}$',
                        example='12345678901'
                    ),
                ],
                'payment_methods': [
                    PaymentMethod('pix', 'PIX', True, 0, Decimal('0.00')),
                    PaymentMethod('ted', 'TED', True, 1, Decimal('0.01')),
                    PaymentMethod('boleto', 'Boleto Bancário', True, 3, Decimal('0.02')),
                ],
                'legal_requirements': [
                    LegalRequirement(
                        title='Nota Fiscal',
                        description='Electronic invoice for services',
                        document_type='invoice',
                        required=True
                    ),
                    LegalRequirement(
                        title='Contrato Social',
                        description='Company social contract (for PJ)',
                        document_type='pdf',
                        required=True
                    ),
                ],
                'max_payment_per_month': Decimal('50000'),  # BRL
                'contract_type': 'Contrato de Prestação de Serviços',
                'notice_period_days': 15,
                'default_tax_withholding': True,
            },
            
            'DE': {
                'name': 'Germany',
                'currency': 'EUR',
                'currency_symbol': '€',
                'language': 'de',
                'timezone': 'Europe/Berlin',
                'tax_rules': [
                    TaxRule(
                        name='Umsatzsteuer',
                        rate=Decimal('0.19'),
                        description='VAT (Umsatzsteuer) - 19%',
                        applies_to='company'
                    ),
                    TaxRule(
                        name='Gewerbesteuer',
                        rate=Decimal('0.14'),
                        description='Trade Tax - varies by municipality',
                        applies_to='company'
                    ),
                ],
                'compliance_rules': [
                    ComplianceRule(
                        field_name='steuer_id',
                        label='Tax ID (Steuer ID)',
                        required=True,
                        validation_pattern=r'^[0-9]{11}$',
                        example='12345678901'
                    ),
                    ComplianceRule(
                        field_name='ust_id',
                        label='VAT ID (USt-IdNr.)',
                        required=False,
                        validation_pattern=r'^DE[0-9]{9}$',
                        example='DE123456789'
                    ),
                    ComplianceRule(
                        field_name='iban',
                        label='IBAN',
                        required=True,
                        validation_pattern=r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}$',
                        example='DE89370400440532013000'
                    ),
                ],
                'payment_methods': [
                    PaymentMethod('sepa', 'SEPA Transfer', True, 2, Decimal('0.00')),
                    PaymentMethod('sepa_instant', 'SEPA Instant', True, 0, Decimal('0.005')),
                ],
                'legal_requirements': [
                    LegalRequirement(
                        title='Datenschutzerklärung',
                        description='GDPR Privacy Policy',
                        document_type='pdf',
                        required=True
                    ),
                    LegalRequirement(
                        title='AGB',
                        description='Terms of Service (AGB)',
                        document_type='pdf',
                        required=True
                    ),
                ],
                'max_payment_per_month': Decimal('10000'),  # EUR
                'contract_type': 'Dienstleistungsvertrag',
                'notice_period_days': 14,
                'default_tax_withholding': False,
            }
        }
        return rules.get(self.country_code, {})
    
    def validate_compliance_fields(self, data: dict) -> Dict:
        """Validate compliance fields for the country"""
        errors = {}
        for rule in self.rules.get('compliance_rules', []):
            if rule.required:
                value = data.get(rule.field_name, '')
                if not value:
                    errors[rule.field_name] = f"{rule.label} is required for {self.rules['name']}"
                elif rule.validation_pattern:
                    import re
                    if not re.match(rule.validation_pattern, value):
                        errors[rule.field_name] = f"Invalid format for {rule.label}. Expected: {rule.example}"
        return errors
    
    def calculate_tax(self, amount_usd: Decimal, exchange_rate: Decimal = Decimal('1')) -> Dict:
        """Calculate taxes for the country"""
        amount_local = amount_usd * exchange_rate
        taxes = []
        total_tax = Decimal('0')
        
        for tax in self.rules.get('tax_rules', []):
            tax_amount = amount_local * tax.rate
            taxes.append({
                'name': tax.name,
                'rate': float(tax.rate),
                'amount_local': float(tax_amount),
                'currency': self.rules.get('currency'),
                'applies_to': tax.applies_to,
            })
            total_tax += tax_amount
        
        return {
            'gross_amount_local': float(amount_local),
            'total_tax': float(total_tax),
            'net_amount_local': float(amount_local - total_tax),
            'taxes': taxes,
            'currency': self.rules.get('currency'),
        }
    
    def get_contract_template_variables(self, company, contractor) -> Dict:
        """Get country-specific variables for contract generation"""
        return {
            'legal_entity': self.rules.get('legal_entity', company.name),
            'contract_type': self.rules.get('contract_type'),
            'notice_period_days': self.rules.get('notice_period_days'),
            'governing_law': self.rules.get('name'),
            'currency_symbol': self.rules.get('currency_symbol'),
            'language': self.rules.get('language'),
        }
    
    def get_available_payment_methods(self) -> List[Dict]:
        """Get available payment methods for the country"""
        return [
            {
                'code': pm.code,
                'name': pm.name,
                'processing_days': pm.processing_days,
                'fee_percentage': float(pm.fee_percentage),
            }
            for pm in self.rules.get('payment_methods', [])
            if pm.available
        ]
    
    def get_compliance_summary(self) -> Dict:
        """Get compliance summary for the country"""
        return {
            'country': self.rules.get('name'),
            'required_fields': [
                {
                    'field': rule.field_name,
                    'label': rule.label,
                    'example': rule.example,
                }
                for rule in self.rules.get('compliance_rules', [])
                if rule.required
            ],
            'tax_rules': [
                {
                    'name': tax.name,
                    'rate': f"{float(tax.rate) * 100}%",
                    'applies_to': tax.applies_to,
                }
                for tax in self.rules.get('tax_rules', [])
            ],
            'max_payment_per_month': f"{self.rules.get('currency_symbol')}{self.rules.get('max_payment_per_month')}",
        }