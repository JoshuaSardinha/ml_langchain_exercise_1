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

class PredictionRequest(BaseModel):
    patient_data: PatientData
    model_type: Literal["copd", "alt"] = Field(..., description="Type of prediction to make")

class PredictionResponse(BaseModel):
    prediction: Any = Field(..., description="Model prediction result")
    confidence: Optional[float] = Field(None, description="Prediction confidence score")
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Feature importance scores")
    model_type: str = Field(..., description="Type of model used")
    patient_id: Optional[str] = Field(None, description="Patient identifier")

class DataQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query about the data")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional data filters")

class DataQueryResponse(BaseModel):
    result: Any = Field(..., description="Query result data")
    visualization: Optional[Dict[str, Any]] = Field(None, description="Chart/visualization data")
    summary: str = Field(..., description="Human-readable summary")
    count: Optional[int] = Field(None, description="Number of records returned")

class DocumentSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for medical documents")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")
    similarity_threshold: float = Field(0.7, ge=0, le=1, description="Minimum similarity score")

class DocumentResult(BaseModel):
    document_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Relevant content excerpt")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional document metadata")

class DocumentSearchResponse(BaseModel):
    results: List[DocumentResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of documents found")
    query: str = Field(..., description="Original search query")

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[ChatMessage]] = Field([], description="Previous messages")
    session_id: Optional[str] = Field(None, description="Session identifier")

class ChatResponse(BaseModel):
    message: str = Field(..., description="AI response")
    message_type: Literal["text", "data", "prediction", "document"] = Field(..., description="Response type")
    data: Optional[Any] = Field(None, description="Additional data payload")
    session_id: str = Field(..., description="Session identifier")
    suggestions: Optional[List[str]] = Field(None, description="Suggested follow-up queries")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    models_loaded: bool = Field(..., description="Whether ML models are loaded")
    vectordb_ready: bool = Field(..., description="Whether vector database is ready")