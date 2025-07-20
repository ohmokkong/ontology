"""
Core data models for exercise API integration.

This module contains the data classes and validation logic for exercise data
retrieved from the Korean Health Promotion Institute's mobile healthcare API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union
from rdflib import URIRef, Namespace
import re


@dataclass
class ExerciseItem:
    """
    Represents an exercise with its metadata from the API.
    
    Attributes:
        name: Exercise name in Korean
        description: Detailed description of the exercise
        met_value: Metabolic Equivalent of Task (MET) coefficient
        category: Optional exercise category
    """
    name: str
    description: str
    met_value: float
    category: Optional[str] = None
    
    def __post_init__(self):
        """Validate the exercise item data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate exercise item data.
        
        Raises:
            ValueError: If any validation fails
        """
        if not self.name or not self.name.strip():
            raise ValueError("Exercise name cannot be empty")
        
        if not self.description or not self.description.strip():
            raise ValueError("Exercise description cannot be empty")
        
        if not isinstance(self.met_value, (int, float)) or self.met_value <= 0:
            raise ValueError("MET value must be a positive number")
        
        if self.met_value > 20:  # Reasonable upper bound for MET values
            raise ValueError("MET value seems unreasonably high (>20)")
        
        # Clean up whitespace
        self.name = self.name.strip()
        self.description = self.description.strip()
        if self.category:
            self.category = self.category.strip()
    
    def to_uri(self, namespace: Namespace) -> URIRef:
        """
        Convert exercise name to a valid URI within the given namespace.
        
        Args:
            namespace: RDF namespace to use
            
        Returns:
            URIRef for this exercise
        """
        # Normalize name for URI: remove special characters, replace spaces with underscores
        normalized_name = re.sub(r'[^\w\s-]', '', self.name)
        normalized_name = re.sub(r'\s+', '_', normalized_name)
        normalized_name = normalized_name.strip('_')
        
        if not normalized_name:
            raise ValueError(f"Cannot create valid URI from exercise name: {self.name}")
        
        return namespace[f"Exercise_{normalized_name}"]


@dataclass
class ExerciseSession:
    """
    Represents a specific exercise session performed by a user.
    
    Attributes:
        exercise_uri: URI reference to the exercise performed
        weight: User's weight in kilograms
        duration: Exercise duration in minutes
        calories_burned: Calculated calories burned
        timestamp: When the exercise was performed
    """
    exercise_uri: URIRef
    weight: float
    duration: float
    calories_burned: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate the exercise session data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate exercise session data.
        
        Raises:
            ValueError: If any validation fails
        """
        if not isinstance(self.exercise_uri, URIRef):
            raise ValueError("exercise_uri must be a URIRef")
        
        if not isinstance(self.weight, (int, float)) or self.weight <= 0:
            raise ValueError("Weight must be a positive number")
        
        if self.weight > 500:  # Reasonable upper bound
            raise ValueError("Weight seems unreasonably high (>500kg)")
        
        if not isinstance(self.duration, (int, float)) or self.duration <= 0:
            raise ValueError("Duration must be a positive number")
        
        if self.duration > 1440:  # More than 24 hours
            raise ValueError("Duration seems unreasonably long (>24 hours)")
        
        if not isinstance(self.calories_burned, (int, float)) or self.calories_burned < 0:
            raise ValueError("Calories burned must be a non-negative number")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
    
    @classmethod
    def create_with_calculation(
        cls,
        exercise_uri: URIRef,
        weight: float,
        duration: float,
        met_value: float,
        timestamp: Optional[datetime] = None
    ) -> 'ExerciseSession':
        """
        Create an exercise session with automatic calorie calculation.
        
        Args:
            exercise_uri: URI reference to the exercise
            weight: User's weight in kg
            duration: Exercise duration in minutes
            met_value: MET coefficient for the exercise
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            ExerciseSession with calculated calories
        """
        calories_burned = cls.calculate_calories(met_value, weight, duration)
        
        return cls(
            exercise_uri=exercise_uri,
            weight=weight,
            duration=duration,
            calories_burned=calories_burned,
            timestamp=timestamp or datetime.now()
        )
    
    @staticmethod
    def calculate_calories(met_value: float, weight: float, duration_minutes: float) -> float:
        """
        Calculate calories burned using the MET formula.
        
        Formula: MET × weight(kg) × time(hours)
        
        Args:
            met_value: Metabolic Equivalent of Task
            weight: Weight in kilograms
            duration_minutes: Duration in minutes
            
        Returns:
            Calories burned (kcal)
        """
        if met_value <= 0 or weight <= 0 or duration_minutes <= 0:
            raise ValueError("All values must be positive for calorie calculation")
        
        duration_hours = duration_minutes / 60.0
        return met_value * weight * duration_hours


# Type aliases for better code readability
ExerciseData = Union[ExerciseItem, ExerciseSession]