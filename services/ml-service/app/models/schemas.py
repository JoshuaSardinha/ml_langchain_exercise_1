from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

class SexEnum(str, Enum):
    MALE = "Male"
    FEMALE = "Female"

class SmokerEnum(str, Enum):
    YES = "Yes"
    NO = "No"

class ExerciseFrequencyEnum(str, Enum):
    NONE = "None"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"

class DietQualityEnum(str, Enum):
    POOR = "Poor"
    AVERAGE = "Average"
    GOOD = "Good"

class IncomeBracketEnum(str, Enum):
    LOW = "Low"
    MIDDLE = "Middle"
    HIGH = "High"

class EducationLevelEnum(str, Enum):
    PRIMARY = "Primary"
    SECONDARY = "Secondary"
    TERTIARY = "Tertiary"

class COPDClassEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class PatientData(BaseModel):
    patient_id: Optional[str] = None
    age: int = Field(..., ge=0, le=120, description="Patient age in years")
    sex: SexEnum = Field(..., description="Patient sex")
    bmi: float = Field(..., ge=10, le=50, description="Body Mass Index")
    smoker: SmokerEnum = Field(..., description="Smoking status")
    diagnosis_code: str = Field(..., description="Primary diagnosis code")
    medication_count: int = Field(..., ge=0, description="Number of medications")
    days_hospitalized: int = Field(..., ge=0, description="Days in hospital")
    readmitted: int = Field(..., ge=0, le=1, description="Readmission flag (0/1)")
    last_lab_glucose: float = Field(..., ge=0, description="Last glucose level")
    exercise_frequency: ExerciseFrequencyEnum = Field(..., description="Exercise frequency")
    diet_quality: DietQualityEnum = Field(..., description="Diet quality assessment")
    income_bracket: IncomeBracketEnum = Field(..., description="Income level")
    education_level: EducationLevelEnum = Field(..., description="Education level")
    urban: int = Field(..., ge=0, le=1, description="Urban residence flag (0/1)")
    albumin_globulin_ratio: float = Field(..., ge=0, description="Lab ratio value")

