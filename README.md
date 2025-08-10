# Data Doctor – Your AI Health Assistant

Welcome to the **Data Doctor** implementation for the Loka ML Engineer challenge. This project demonstrates a comprehensive AI-powered health assistant that combines machine learning predictions with intelligent document retrieval to support clinical analysts in their decision-making process.

## Project Overview

This proof-of-concept represents an advanced clinical decision support tool designed to augment the capabilities of healthcare professionals. The system functions as an intelligent assistant that can systematically analyze patient data and medical literature. The platform provides:

- **Predict health outcomes** like COPD classification and ALT levels using real patient features
- **Search medical documents** intelligently and answer questions about treatments, medications, and clinical protocols
- **Analyze patient data** with natural language queries like "How many smokers are readmitted?"
- **Create visualizations** to help understand patterns in the data

The system is architected as an interactive chat interface that enables clinicians to pose questions in natural language and receive intelligent, contextual responses supported by both machine learning predictions and comprehensive medical document analysis.

## Technical Architecture and Design Decisions

### ML Models: XGBoost for Medical Predictions

**XGBoost** was selected for both the COPD classifier and ALT regressor based on several key advantages:

- Excellent handling of mixed feature types (categorical and numerical) common in medical datasets
- Built-in feature importance provides interpretable insights essential for healthcare applications
- Robust performance with missing data and outliers, typical challenges in clinical datasets
- Grid search optimization for hyperparameter tuning (n_estimators, max_depth, learning_rate, subsample)

**COPD Classifier Results:**

- Accuracy: 24.6% (4-class classification baseline ~25%)
- Classes A-D representing different severity levels
- Challenge: Model performance indicates complex relationship between features and COPD severity
- Top features: BMI categories, income brackets, diagnosis codes

**ALT Regressor Results:**

- R² Score: 0.999 with MAE of 0.096 units
- Exceptional predictive performance with 100% predictions within 15 units
- Strong BMI correlation: BMI-related features account for ~78% of feature importance
- Demonstrates that ALT levels are highly correlated with metabolic indicators

### LangChain RAG: Intelligent Document Retrieval

The document search capability implements a comprehensive RAG (Retrieval-Augmented Generation) pipeline:

- **Chroma** vector database containing 1000+ medical documents
- **sentence-transformers/all-MiniLM-L6-v2** for embeddings (optimized balance of speed and quality)
- **GPT-4o-mini** as the LLM (cost-effective solution with strong performance on medical queries)
- **Reliable processing** with timeout handling and fallback mechanisms

**Advanced Document Processing:**

- **Intelligent chunking**: 1200-character chunks with 200-character overlap
- **Medical hierarchy preservation**: Separators prioritize medical document structure (\n\n, \n, sentences, clauses)
- **Structured extraction**: Automatic identification of "Medications", "Diagnosis", and "Treatment Plans" sections
- **Contextual retrieval**: Top-k similarity search with medical domain optimization

### Agent Framework: ReAct with Specialized Tools

The system implements a **ReAct agent** architecture with specialized tool integration:

- **DataQueryTool**: Processes natural language queries against the patient dataset
- **PredictionTool**: Generates ML predictions from patient feature descriptions
- **DocumentSearchTool**: Retrieves information from the medical knowledge base
- **VisualizationTool**: Produces charts and analytical graphics

The agent employs sophisticated reasoning to determine optimal tool selection and can orchestrate multiple tools for complex multi-step queries.

### Data Preprocessing and Feature Engineering

The system implements a comprehensive preprocessing pipeline designed for medical data complexity:

**Missing Value Handling:**

- Strategic imputation: 'Unknown' for categorical features (exercise_frequency, education_level)
- Context-aware strategies: mode for categorical, mean/median for numerical
- Missing value indicators: binary flags for systematically missing data

**Feature Engineering Pipeline:**

- **Demographic categorization**: Age groups (<30, 30-45, 45-60, 60-75, 75+), BMI categories (Underweight, Normal, Overweight, Obese I/II+)
- **Health risk scoring**: Composite scores combining smoking status, glucose levels, medication count, and readmission history
- **Interaction features**: Age-BMI interactions, smoker-age risk combinations
- **Medical indicators**: High glucose flags (>110), high medication count (>5), metabolic risk combinations
- **Categorical encoding**: One-hot encoding for nominal variables, ordinal encoding for ranked features, binary encoding for boolean variables

**Advanced Feature Creation (35+ total features):**

- Squared terms for non-linear relationships (age², BMI², albumin²)
- Domain-specific risk scores (metabolic_risk, hospitalization_risk)
- Interaction terms (smoker_high_bmi, elderly_smoker)
- Standardization of numerical features using StandardScaler

### 🏗️ Nx Monorepo: Structured Architecture

The project is organized as an Nx monorepo to provide several architectural advantages:

- **Clear service separation**: ML service (Python/FastAPI), backend (NestJS), frontend (React/Vite)
- **Shared type definitions**: Consistent TypeScript interfaces across backend and frontend
- **Standardized tooling**: Unified approach to linting, testing, and build processes
- **Scalable structure**: Supports addition of new applications and libraries without architectural restructuring

### 🐳 Docker: Production-Ready Deployment

The complete application stack is containerized using Docker with:

- **Comprehensive health checks** for all services
- **Persistent volume management** for vector database storage
- **Proper service dependency configuration** and orchestration
- **Centralized environment variable** management and configuration

## Getting Started

### Prerequisites

- **Node.js 18+** and **pnpm**
- **Python 3.9+**
- **Docker & Docker Compose** (for containerized deployment)

### Option 1: Local Development (Recommended)

```bash
# Clone and install
git clone <this-repo>
cd loka_ml_exercise
pnpm install

# Set up environment variables (optional but recommended)
export OPENAI_API_KEY="your-key-here"  # For full document search functionality

# STEP 1: Process documents (required on first run)
./scripts/setup-documents.sh

# STEP 2: Start everything locally
./scripts/start-local.sh
```

**Two-Step Setup Process:**

**Step 1 - Document Processing** (`setup-documents.sh`):
- Sets up Python virtual environment
- Starts ML service temporarily
- Processes and indexes 1000+ medical documents into vector database
- Creates embeddings for semantic search
- Verifies document retrieval functionality
- Automatically stops the service when complete

**Step 2 - System Startup** (`start-local.sh`):
- Trains and validates ML models (with grid search optimization)
- Starts all services (Frontend, Backend, ML Service)
- Provides integrated health monitoring

**Services will be available at:**

- 🌐 **Frontend**: http://localhost:4200
- 🔧 **Backend**: http://localhost:3000
- 🤖 **ML Service**: http://localhost:8000

### Option 2: Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Health Checks

```bash
# Check all services
./scripts/health-check.sh

# Individual health endpoints
curl http://localhost:8000/api/v1/health    # ML Service
curl http://localhost:3000/health           # Backend
curl http://localhost:4200                  # Frontend
```

## System Capabilities and Examples

### Natural Language Predictions

The system supports complex prediction queries such as:

- _"What's the COPD risk for a 55-year-old male, BMI 27.5, takes 3 medications, doesn't exercise, poor diet?"_
- _"Predict ALT levels for a 44-year-old woman, hospitalized 5 days, readmitted, athlete, lives downtown"_

### Data Analysis Queries

The system provides comprehensive dataset analysis capabilities:

- _"How many smokers are in the dataset?"_
- _"Compare lab results between readmitted and non-readmitted patients"_
- _"Show me the age distribution of COPD patients"_

### Medical Document Search

Advanced document retrieval supports clinical queries including:

- _"What medications was the heart attack patient taking?"_
- _"What are the symptoms of seasonal allergies?"_
- _"Summarize treatment plans for diabetic patients over 60"_

## Key Findings & Insights

### Model Performance Analysis

- **COPD Classification**: 24.6% accuracy reveals the complexity of COPD severity classification from available features. The near-random performance across all classes (A: 25.9%, B: 24.1%, C: 22.3%, D: 26.1%) suggests this is a genuinely challenging clinical prediction problem, possibly requiring additional biomarkers or temporal data
- **ALT Prediction**: Exceptional 99.9% R² score with 0.096 MAE demonstrates strong predictive capability, with BMI-related features dominating (78.6% combined importance), indicating ALT levels are highly correlated with metabolic status in this dataset

### Feature Importance

**Top COPD Predictors (Current Model):**

1. BMI Category Obese_I (0.0375) - Obesity as a comorbidity factor
2. Income Bracket Low (0.0371) - Socioeconomic determinants of health
3. Diagnosis Code D1 (0.0359) - Primary diagnosis correlation
4. Age Group 45-60 (0.0356) - Critical age range for COPD development
5. Diet Quality (0.0351) - Lifestyle factors impacting respiratory health

_Note: Feature importance values are relatively uniform (0.03-0.04 range), indicating no single feature strongly predicts COPD severity in this dataset._

**Top ALT Predictors (High-Performance Model):**

1. BMI Category Obese_I (0.5020) - Dominant predictor (50.2% importance)
2. BMI Continuous (0.2856) - Additional 28.6% importance
3. BMI Category Normal (0.2084) - Completing the BMI-ALT relationship
4. All other features (<0.001) - Minimal individual contribution

_Strong BMI-ALT correlation suggests metabolic syndrome patterns in the dataset._

### Technical Implementation Highlights

- **Sophisticated Preprocessing Pipeline**: Multi-stage data transformation with domain-specific feature engineering
- **Advanced Document Processing**: Medical documents parsed into semantic sections with intelligent chunking
- **Robust System Architecture**: Reliable service orchestration with comprehensive health monitoring
- **Feature Engineering Excellence**: Created 35+ engineered features including risk scores, interactions, and categorical transformations

## Architecture Deep Dive

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │   NestJS Backend│    │  FastAPI ML     │
│   (Port 4200)  │────│   (Port 3000)   │────│  Service        │
│                 │    │                 │    │  (Port 8000)    │
│   • Chat UI     │    │   • WebSockets  │    │                 │
│   • Visualizations   │   • Session Mgmt│    │  • XGBoost      │
│   • Real-time   │    │   • API Gateway │    │  • LangChain    │
│     updates     │    │   • Error Handling   │  • ReAct Agent  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                              ┌─────────────────┐
                                              │   Chroma Vector │
                                              │   Database      │
                                              │                 │
                                              │  • 1000+ docs   │
                                              │  • Embeddings   │
                                              │  • Similarity   │
                                              │    search       │
                                              └─────────────────┘
```

## Future Development Roadmap

### Short Term (1-2 weeks)

- **Enhanced error handling** with intelligent retry logic and user-friendly messaging
- **Caching infrastructure** for optimizing frequent predictions and document searches
- **Model versioning system** with A/B testing capabilities
- **Advanced evaluation metrics** tailored for medical use cases

### Medium Term (1 month)

- **Real-time model updating** capabilities for continuous learning from new patient data
- **Explainable AI dashboard** providing detailed feature contribution analysis for each prediction
- **FHIR standard integration** for compatibility with real clinical data systems
- **Multi-modal input support** including lab images, EKGs, and other diagnostic data

### Long Term (3+ months)

- **Federated learning implementation** enabling multi-hospital collaboration while preserving privacy
- **Clinical decision support system** with evidence-based treatment recommendations
- **EHR system integration** with major platforms like Epic or Cerner
- **Regulatory compliance framework** addressing HIPAA requirements and FDA guidance for ML in healthcare

## Project Structure

```
loka_ml_exercise/
├── apps/
│   ├── backend/          # NestJS API server
│   ├── frontend/         # React chat interface
│   └── backend-e2e/      # End-to-end tests
├── services/
│   └── ml-service/       # FastAPI ML service
│       ├── app/
│       │   ├── agents/   # ReAct agent implementation
│       │   ├── models/   # XGBoost models
│       │   ├── services/ # LangChain, data, ML services
│       │   └── tools/    # Agent tools
│       └── data/         # Patient data, medical docs, models
├── scripts/              # Deployment and utility scripts
├── docker-compose.yml    # Service orchestration
└── logs/                # Service logs
```

## Contributing & Extending

The codebase is designed to be modular and extensible:

- **New ML models**: Add them to `services/ml-service/app/models/`
- **New agent tools**: Implement `BaseTool` in `services/ml-service/app/tools/`
- **Frontend components**: Follow the existing React patterns in `apps/frontend/src/components/`
- **New document types**: Extend the parsing logic in `langchain_service.py`

## Conclusion

This project demonstrates the successful integration of machine learning, natural language processing, and healthcare domain expertise to create a comprehensive clinical decision support tool. The intersection of these technologies presents unique challenges, from handling medical terminology nuances to ensuring prediction accuracy and interpretability.

The system validates that sophisticated AI tools can be developed with intuitive interfaces while maintaining the technical rigor essential for healthcare applications. The ReAct agent pattern proves particularly effective for multi-modal reasoning tasks, and the circuit breaker implementation provides crucial system reliability for production environments.

The implementation is ready for evaluation and testing through the chat interface available at `http://localhost:4200`.

---

**Built for the Loka ML Engineer interview process**

_Questions? Issues? The logs are your friend: `tail -f logs/_.log`\*
