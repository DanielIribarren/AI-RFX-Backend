"""
✅ Validation Utilities - Reusable validators for data validation
Centralized validation logic with consistent error handling
"""
import re
from datetime import datetime
from typing import Union, Optional
from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """Base class for all validators"""
    
    @abstractmethod
    def validate(self, value: str) -> bool:
        """Validate the given value"""
        pass
    
    @abstractmethod
    def get_error_message(self, value: str) -> str:
        """Get error message for invalid value"""
        pass


class EmailValidator(BaseValidator):
    """Email format validator"""
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate(self, email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(self.EMAIL_PATTERN.match(email.strip()))
    
    def get_error_message(self, email: str) -> str:
        return f"Invalid email format: '{email}'"


class DateValidator(BaseValidator):
    """Date format validator (YYYY-MM-DD)"""
    
    DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    
    def validate(self, date_str: str) -> bool:
        """Validate date format and actual date"""
        if not date_str or not isinstance(date_str, str):
            return False
        
        # Check format first
        if not self.DATE_PATTERN.match(date_str.strip()):
            return False
        
        # Check if it's a valid date
        try:
            datetime.strptime(date_str.strip(), '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def get_error_message(self, date_str: str) -> str:
        return f"Invalid date format (expected YYYY-MM-DD): '{date_str}'"


class TimeValidator(BaseValidator):
    """Time format validator (HH:MM in 24h format)"""
    
    TIME_PATTERN = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$')
    
    def validate(self, time_str: str) -> bool:
        """Validate time format"""
        if not time_str or not isinstance(time_str, str):
            return False
        return bool(self.TIME_PATTERN.match(time_str.strip()))
    
    def get_error_message(self, time_str: str) -> str:
        return f"Invalid time format (expected HH:MM): '{time_str}'"


class ProductValidator:
    """Validator for product data structures"""
    
    @staticmethod
    def validate_product(product: dict) -> bool:
        """Validate product dictionary structure"""
        required_fields = ['nombre', 'cantidad', 'unidad']
        
        if not isinstance(product, dict):
            return False
        
        # Check required fields
        for field in required_fields:
            if field not in product or not product[field]:
                return False
        
        # Validate specific field types and values
        try:
            # nombre must be non-empty string
            if not isinstance(product['nombre'], str) or not product['nombre'].strip():
                return False
            
            # cantidad must be positive integer
            cantidad = int(product['cantidad'])
            if cantidad <= 0:
                return False
            
            # unidad must be non-empty string
            if not isinstance(product['unidad'], str) or not product['unidad'].strip():
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_product_list(products: list) -> bool:
        """Validate list of products"""
        if not isinstance(products, list) or not products:
            return False
        
        return all(ProductValidator.validate_product(p) for p in products)


class RFXDataValidator:
    """Comprehensive validator for RFX data"""
    
    def __init__(self):
        self.email_validator = EmailValidator()
        self.date_validator = DateValidator()
        self.time_validator = TimeValidator()
    
    def validate_rfx_data(self, data: dict) -> tuple[bool, list[str]]:
        """
        Validate complete RFX data structure
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate email
        email = data.get('email', '')
        if not self.email_validator.validate(email):
            errors.append(self.email_validator.get_error_message(email))
        
        # Validate date
        fecha = data.get('fecha', '')
        if not self.date_validator.validate(fecha):
            errors.append(self.date_validator.get_error_message(fecha))
        
        # Validate time
        hora = data.get('hora_entrega', '')
        if not self.time_validator.validate(hora):
            errors.append(self.time_validator.get_error_message(hora))
        
        # Validate required text fields
        required_text_fields = ['nombre_solicitante', 'lugar']
        for field in required_text_fields:
            value = data.get(field, '')
            if not value or not isinstance(value, str) or not value.strip():
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate products
        productos = data.get('productos', [])
        if not ProductValidator.validate_product_list(productos):
            errors.append("Invalid or empty products list")
        
        return len(errors) == 0, errors
    
    def get_validation_summary(self, data: dict) -> dict:
        """Get detailed validation summary"""
        is_valid, errors = self.validate_rfx_data(data)
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "error_count": len(errors),
            "validated_fields": {
                "email": self.email_validator.validate(data.get('email', '')),
                "fecha": self.date_validator.validate(data.get('fecha', '')),
                "hora_entrega": self.time_validator.validate(data.get('hora_entrega', '')),
                "productos": ProductValidator.validate_product_list(data.get('productos', []))
            }
        }


# Convenience functions for quick validation
def validate_email(email: str) -> bool:
    """Quick email validation"""
    return EmailValidator().validate(email)


def validate_date(date_str: str) -> bool:
    """Quick date validation"""
    return DateValidator().validate(date_str)


def validate_time(time_str: str) -> bool:
    """Quick time validation"""
    return TimeValidator().validate(time_str)
