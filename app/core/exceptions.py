"""
Exceptions personnalisées pour l'API de traitement de documents.
"""

from typing import Optional, Dict, Any


class DocumentProcessingException(Exception):
    """Exception de base."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(DocumentProcessingException):
    """Erreur d'authentification."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(DocumentProcessingException):
    """Erreur d'autorisation."""

    def __init__(self, message: str = "Access denied", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details
        )


class ValidationError(DocumentProcessingException):
    """Erreur de validation."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class DocumentStructureError(DocumentProcessingException):
    """Erreur de structure du document (pas de markdown détecté)."""

    def __init__(self, message: str = "Document structure not detected", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="STRUCTURE_NOT_DETECTED",
            status_code=422,
            details=details
        )


class OCRProcessingError(DocumentProcessingException):
    """Erreur traitement OCR."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="OCR_PROCESSING_ERROR",
            status_code=500,
            details=details
        )


class EnrichmentError(DocumentProcessingException):
    """Erreur enrichissement."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="ENRICHMENT_ERROR",
            status_code=500,
            details=details
        )


class MistralAPIError(DocumentProcessingException):
    """Erreur API Mistral."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="MISTRAL_API_ERROR",
            status_code=502,
            details=details
        )


class RateLimitError(DocumentProcessingException):
    """Dépassement rate limit."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class TimeoutError(DocumentProcessingException):
    """Timeout."""

    def __init__(self, message: str = "Request timeout", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="TIMEOUT",
            status_code=504,
            details=details
        )
