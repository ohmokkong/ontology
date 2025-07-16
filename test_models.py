"""
Basic tests to verify the data models work correctly.
"""

from datetime import datetime
from rdflib import Namespace, URIRef
from models import ExerciseItem, ExerciseSession
from exceptions import DataValidationError
import traceback


def test_exercise_item():
    """Test ExerciseItem creation and validation."""
    print("Testing ExerciseItem...")
    
    # Test valid exercise item
    try:
        exercise = ExerciseItem(
            name="달리기",
            description="일반적인 달리기 운동",
            met_value=8.0,
            category="유산소"
        )
        print(f"✓ Valid exercise created: {exercise.name}")
        
        # Test URI generation
        namespace = Namespace("http://example.org/diet#")
        uri = exercise.to_uri(namespace)
        print(f"✓ URI generated: {uri}")
        
    except Exception as e:
        print(f"✗ Error creating valid exercise: {e}")
        traceback.print_exc()
    
    # Test invalid exercise item (empty name)
    try:
        invalid_exercise = ExerciseItem(
            name="",
            description="Test",
            met_value=5.0
        )
        print("✗ Should have failed with empty name")
    except ValueError as e:
        print(f"✓ Correctly caught empty name error: {e}")
    
    # Test invalid MET value
    try:
        invalid_exercise = ExerciseItem(
            name="Test Exercise",
            description="Test",
            met_value=-1.0
        )
        print("✗ Should have failed with negative MET value")
    except ValueError as e:
        print(f"✓ Correctly caught negative MET error: {e}")


def test_exercise_session():
    """Test ExerciseSession creation and validation."""
    print("\nTesting ExerciseSession...")
    
    namespace = Namespace("http://example.org/diet#")
    exercise_uri = namespace["Exercise_Running"]
    
    # Test valid exercise session
    try:
        session = ExerciseSession(
            exercise_uri=exercise_uri,
            weight=70.0,
            duration=30.0,
            calories_burned=280.0
        )
        print(f"✓ Valid session created: {session.duration} minutes")
        
    except Exception as e:
        print(f"✗ Error creating valid session: {e}")
        traceback.print_exc()
    
    # Test session with calculation
    try:
        session = ExerciseSession.create_with_calculation(
            exercise_uri=exercise_uri,
            weight=70.0,
            duration=30.0,
            met_value=8.0
        )
        expected_calories = 8.0 * 70.0 * 0.5  # 30 minutes = 0.5 hours
        print(f"✓ Session with calculation: {session.calories_burned} kcal (expected: {expected_calories})")
        
    except Exception as e:
        print(f"✗ Error creating session with calculation: {e}")
        traceback.print_exc()
    
    # Test invalid weight
    try:
        invalid_session = ExerciseSession(
            exercise_uri=exercise_uri,
            weight=-10.0,
            duration=30.0,
            calories_burned=100.0
        )
        print("✗ Should have failed with negative weight")
    except ValueError as e:
        print(f"✓ Correctly caught negative weight error: {e}")


def test_calorie_calculation():
    """Test calorie calculation formula."""
    print("\nTesting calorie calculation...")
    
    # Test standard calculation
    calories = ExerciseSession.calculate_calories(8.0, 70.0, 30.0)
    expected = 8.0 * 70.0 * 0.5  # 280 kcal
    print(f"✓ Calorie calculation: {calories} kcal (expected: {expected})")
    
    # Test invalid inputs
    try:
        invalid_calories = ExerciseSession.calculate_calories(-1.0, 70.0, 30.0)
        print("✗ Should have failed with negative MET")
    except ValueError as e:
        print(f"✓ Correctly caught negative MET in calculation: {e}")


if __name__ == "__main__":
    test_exercise_item()
    test_exercise_session()
    test_calorie_calculation()
    print("\n✓ All tests completed!")