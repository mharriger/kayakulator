"""Property definition for the properties panel."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class PropertyType(Enum):
    """Enumeration of property value types."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    COLOR = "color"
    ENUM = "enum"


@dataclass
class PropertyDefinition:
    """Definition of a single property for display in the properties panel.
    
    Attributes:
        name: Internal property key (used to identify property in data dict)
        display_name: User-visible label (shown in properties grid)
        prop_type: PropertyType enum indicating the data type
        editable: Whether this property can be edited
        validator: Optional validation function that takes a value and returns (is_valid, error_msg)
        choices: For enum types, list of (value, display_name) tuples
        min_value: For numeric types, minimum allowed value
        max_value: For numeric types, maximum allowed value
    """
    name: str
    display_name: str
    prop_type: PropertyType
    editable: bool = True
    validator: Optional[Callable[[Any], tuple[bool, str]]] = None
    choices: Optional[list[tuple[Any, str]]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def validate(self, value: Any) -> tuple[bool, str]:
        """Validate a value for this property.
        
        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        if self.validator:
            return self.validator(value)
        
        # Basic type checking
        if self.prop_type == PropertyType.INT:
            try:
                int_val = int(value) if not isinstance(value, int) else value
                if self.min_value is not None and int_val < self.min_value:
                    return False, f"Value must be >= {self.min_value}"
                if self.max_value is not None and int_val > self.max_value:
                    return False, f"Value must be <= {self.max_value}"
                return True, ""
            except (ValueError, TypeError):
                return False, "Must be an integer"
        
        elif self.prop_type == PropertyType.FLOAT:
            try:
                float_val = float(value) if not isinstance(value, float) else value
                if self.min_value is not None and float_val < self.min_value:
                    return False, f"Value must be >= {self.min_value}"
                if self.max_value is not None and float_val > self.max_value:
                    return False, f"Value must be <= {self.max_value}"
                return True, ""
            except (ValueError, TypeError):
                return False, "Must be a number"
        
        elif self.prop_type == PropertyType.BOOL:
            if not isinstance(value, bool):
                return False, "Must be a boolean"
            return True, ""
        
        return True, ""
