"""
JTECH Error Handler — Bulletproof error resilience layer.

Provides:
- Circuit Breaker pattern (prevents cascading failures)
- Exponential backoff retry with jitter
- Graceful fallback chains
- Error classification and recovery strategies
- Comprehensive error logging

No external dependencies — pure Python stdlib.
"""

from __future__ import annotations

import functools
import logging
import random
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── ERROR CLASSIFICATION ────────────────────────────────────────

class ErrorSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    NETWORK = "network"              # API calls, HTTP errors
    DATABASE = "database"            # State storage errors
    FILESYSTEM = "filesystem"        # File read/write errors
    PERMISSION = "permission"        # Access denied
    VALIDATION = "validation"        # Bad input data
    RESOURCE = "resource"            # Out of memory, disk full
    TIMEOUT = "timeout"              # Operation timed out
    UNKNOWN = "unknown"              # Catch-all


# ── CIRCUIT BREAKER ─────────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "closed"          # Normal operation — requests pass through
    OPEN = "open"              # Failure threshold exceeded — requests blocked
    HALF_OPEN = "half_open"    # Testing if service has recovered


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker pattern — prevents cascading failures.

    When a service fails repeatedly, the circuit 'opens' and subsequent
    calls fail fast without attempting the operation. After a timeout,
    it 'half-opens' to test if the service has recovered.

    States: CLOSED → OPEN (on failures) → HALF_OPEN (after timeout) → CLOSED (on success)
    """
    name: str
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: float = 30.0       # Seconds before trying again
    half_open_max_requests: int = 1      # Requests allowed in half-open state

    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: Optional[datetime] = None
    _half_open_requests: int = 0
    _total_failures: int = 0
    _total_successes: int = 0
    _last_error: Optional[str] = None

    def record_failure(self, error: Optional[str] = None) -> None:
        """Record a failure and potentially open the circuit."""
        self._failure_count += 1
        self._total_failures += 1
        self._last_failure_time = datetime.now()
        self._last_error = error

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit [{self.name}] OPEN after {self._failure_count} failures")

    def record_success(self) -> None:
        """Record a success and close the circuit."""
        self._failure_count = 0
        self._half_open_requests = 0
        self._total_successes += 1
        if self._state != CircuitState.CLOSED:
            self._state = CircuitState.CLOSED
            logger.info(f"Circuit [{self.name}] CLOSED — service recovered")

    @property
    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_requests = 0
                    logger.info(f"Circuit [{self.name}] HALF_OPEN — testing recovery")
                    return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_requests < self.half_open_max_requests:
                self._half_open_requests += 1
                return True
            return False

        return False

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def summary(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failures_total": self._total_failures,
            "successes_total": self._total_successes,
            "failure_count": self._failure_count,
            "last_error": self._last_error,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
        }

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._last_error = None


# ── RETRY CONFIG ────────────────────────────────────────────────

@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""
    max_retries: int = 3
    base_delay: float = 1.0          # Initial delay in seconds
    max_delay: float = 30.0          # Maximum delay in seconds
    backoff_multiplier: float = 2.0  # Multiply delay by this each retry
    jitter: bool = True              # Add random jitter to prevent thundering herd
    retryable_exceptions: tuple = (ConnectionError, TimeoutError, OSError)


# ── ERROR HANDLER ───────────────────────────────────────────────

@dataclass
class ErrorHandler:
    """
    Central error handling with circuit breaker + retry + fallback.

    Usage:
        handler = ErrorHandler()
        result = handler.execute(
            operation=my_function,
            fallback=lambda: "default value",
            circuit_name="my-api",
            retry_config=RetryConfig(),
        )
    """

    _circuits: dict[str, CircuitBreaker] = field(default_factory=dict)
    _default_retry: RetryConfig = field(default_factory=RetryConfig)

    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    def execute(
        self,
        operation: Callable[..., T],
        *args: Any,
        fallback: Optional[Callable[..., T]] = None,
        circuit_name: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        **kwargs: Any,
    ) -> T:
        """
        Execute an operation with circuit breaker + retry + fallback.

        Args:
            operation: The function to execute
            fallback: Fallback function if all retries fail
            circuit_name: Name for circuit breaker tracking
            retry_config: Retry configuration

        Returns:
            The operation result or fallback result

        Raises:
            Last exception if no fallback provided and all retries fail
        """
        config = retry_config or self._default_retry
        last_exception: Optional[Exception] = None

        # Check circuit breaker
        if circuit_name:
            circuit = self.get_circuit(circuit_name)
            if not circuit.can_execute:
                error_msg = f"Circuit [{circuit_name}] is {circuit.state}. Request blocked."
                logger.warning(error_msg)
                return self._handle_failure(
                    RuntimeError(error_msg),
                    fallback=fallback,
                    circuit_name=circuit_name,
                )

        # Attempt with retries
        for attempt in range(config.max_retries + 1):
            try:
                result = operation(*args, **kwargs)

                # Record success in circuit breaker
                if circuit_name:
                    self._circuits[circuit_name].record_success()

                return result

            except Exception as e:
                last_exception = e
                error_class = e.__class__.__name__
                error_msg = str(e)[:200]

                # Classify the error
                category = self._classify_error(e)
                severity = ErrorSeverity.WARNING if attempt < config.max_retries else ErrorSeverity.ERROR

                logger.log(
                    logging.WARNING if attempt < config.max_retries else logging.ERROR,
                    f"Attempt {attempt + 1}/{config.max_retries + 1} failed: "
                    f"[{category.value}] {error_class}: {error_msg}"
                )

                # Record failure in circuit breaker
                if circuit_name:
                    self._circuits[circuit_name].record_failure(f"{error_class}: {error_msg}")

                # Check if this error type is retryable
                if not isinstance(e, config.retryable_exceptions) and attempt < config.max_retries:
                    logger.info(f"Non-retryable error ({error_class}) — skipping remaining retries")
                    break

                # Wait before retry (exponential backoff with jitter)
                if attempt < config.max_retries:
                    delay = min(
                        config.base_delay * (config.backoff_multiplier ** attempt),
                        config.max_delay,
                    )
                    if config.jitter:
                        delay *= 0.5 + random.random() * 0.5  # 50-100% of calculated delay
                    time.sleep(delay)

        # All retries exhausted — use fallback or raise
        return self._handle_failure(
            last_exception,
            fallback=fallback,
            circuit_name=circuit_name,
        )

    def _handle_failure(
        self,
        error: Optional[Exception],
        fallback: Optional[Callable[..., Any]] = None,
        circuit_name: Optional[str] = None,
    ) -> Any:
        """Handle a failure by calling fallback or raising."""
        if error:
            logger.error(
                f"Operation failed after retries"
                f"{f' [circuit: {circuit_name}]' if circuit_name else ''}: {error}"
            )

        if fallback:
            try:
                fallback_result = fallback()
                logger.info(f"Fallback executed successfully")
                return fallback_result
            except Exception as fb_error:
                logger.error(f"Fallback also failed: {fb_error}")

        if error:
            raise error

        raise RuntimeError("Operation failed with no error information")

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an exception into an error category."""
        error_name = error.__class__.__name__

        if isinstance(error, (ConnectionError, ConnectionRefusedError, ConnectionResetError)):
            return ErrorCategory.NETWORK
        if isinstance(error, TimeoutError):
            return ErrorCategory.TIMEOUT
        if isinstance(error, (PermissionError, FileNotFoundError)):
            return ErrorCategory.PERMISSION if isinstance(error, PermissionError) else ErrorCategory.FILESYSTEM
        if isinstance(error, (OSError, IOError)):
            return ErrorCategory.FILESYSTEM
        if isinstance(error, (ValueError, TypeError, KeyError)):
            return ErrorCategory.VALIDATION
        if "database" in error_name.lower() or "sql" in error_name.lower():
            return ErrorCategory.DATABASE

        return ErrorCategory.UNKNOWN

    def circuit_summary(self, name: Optional[str] = None) -> list[dict]:
        """Get summary of all circuit breakers (or a specific one)."""
        if name:
            circuit = self._circuits.get(name)
            return [circuit.summary] if circuit else []
        return [c.summary for c in self._circuits.values()]

    def reset_circuit(self, name: str) -> bool:
        """Reset a specific circuit breaker."""
        if name in self._circuits:
            self._circuits[name].reset()
            return True
        return False


# ── CONVENIENCE DECORATOR ───────────────────────────────────────

# Shared handler instance for stateful circuit breakers
_shared_handler = ErrorHandler()


def with_resilience(
    circuit_name: Optional[str] = None,
    max_retries: int = 3,
    fallback: Optional[Callable] = None,
):
    """
    Decorator that wraps a function with error resilience.

    Uses a shared ErrorHandler instance so circuit breaker state
    is preserved across calls.

    Usage:
        @with_resilience(circuit_name="nvidia-api", max_retries=3)
        def call_api():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(max_retries=max_retries)
            return _shared_handler.execute(
                func, *args,
                fallback=fallback,
                circuit_name=circuit_name,
                retry_config=config,
                **kwargs,
            )
        return wrapper
    return decorator
