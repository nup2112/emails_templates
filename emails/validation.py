import re

def validate_email(email):
    """Valida un email según un patrón básico"""
    # Patrón simple para validación de email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_emails(emails):
    """Valida una lista de emails y retorna los válidos e inválidos"""
    valid_emails = []
    invalid_emails = []
    
    for email in emails:
        if validate_email(email):
            valid_emails.append(email)
        else:
            invalid_emails.append(email)
    
    return valid_emails, invalid_emails