import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()
logger = logging.getLogger(__name__)


class LangChainDocumentService:
    """Simplified document service using modern LangChain patterns"""
    
    def __init__(self, 
                 docs_path: str = "data/docs",
                 vectordb_path: str = "data/vectordb_langchain",
                 collection_name: str = "medical_documents"):
        
        self.docs_path = Path(docs_path)
        self.vectordb_path = Path(vectordb_path)
        self.collection_name = collection_name
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,  # Larger chunks for medical documents
            chunk_overlap=200,  # More overlap to preserve context
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        self.llm = self._initialize_llm()
        self.vector_store = self._initialize_vector_store()
        self.rag_chain = self._create_rag_chain()
        
        logger.info("LangChain service initialized successfully")
    
    def _initialize_llm(self) -> Optional[ChatOpenAI]:
        """Initialize OpenAI LLM"""
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_key:
            logger.warning("No OpenAI API key found")
            return None
        
        try:
            llm = ChatOpenAI(
                api_key=openai_key,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=1000
            )
            logger.info("OpenAI LLM initialized successfully")
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {e}")
            return None
    
    def _initialize_vector_store(self) -> Optional[Chroma]:
        """Initialize Chroma vector store"""
        try:
            self.vectordb_path.mkdir(parents=True, exist_ok=True)
            
            vector_store = Chroma(
                persist_directory=str(self.vectordb_path),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            
            logger.info("Vector store initialized successfully")
            return vector_store
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return None
    
    def _create_rag_chain(self):
        """Create a simple RAG chain using LCEL"""
        if not self.llm or not self.vector_store:
            logger.warning("Cannot create RAG chain - LLM or vector store not available")
            return None
        
        # Create retriever
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        
        # Create enhanced medical prompt template
        prompt = ChatPromptTemplate.from_template("""
You are a specialized medical assistant analyzing clinical documents. Use the provided context to answer medical questions accurately.

Context: {context}

Question: {question}

Instructions:
- For medication queries, provide structured information including dosage, frequency, and duration
- For patient-specific questions, extract relevant details from the medical sections
- For heart attack/myocardial infarction queries, focus on cardiac medications and treatment protocols
- If information is not in the context, clearly state this limitation
- Provide specific citations when possible (patient ID, document type, section)

Answer:""")
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        logger.info("RAG chain created successfully")
        return rag_chain
    
    def _extract_medical_sections(self, document: Document) -> List[Document]:
        """Extract medical sections from document content"""
        content = document.page_content
        metadata = document.metadata.copy()
        
        patient_id = self._extract_patient_id(content)
        document_type = self._extract_document_type(content)
        diagnoses = self._extract_diagnoses(content)
        
        metadata.update({
            'patient_id': patient_id or 'unknown',
            'document_type': document_type or 'medical_document',
            'diagnoses': ', '.join(diagnoses) if diagnoses else ''
        })
        
        section_patterns = {
            'patient_info': r'## Patient Information.*?(?=##|\Z)',
            'chief_complaint': r'## Chief Complaint.*?(?=##|\Z)',
            'history': r'## History.*?(?=##|\Z)',
            'vitals': r'## Vitals.*?(?=##|\Z)',
            'diagnosis': r'## Diagnosis.*?(?=##|\Z)',
            'medications': r'## Medications.*?(?=##|\Z)',
            'treatment': r'## Treatment.*?(?=##|\Z)',
            'lab_results': r'## Lab Results.*?(?=##|\Z)',
            'imaging': r'## Imaging.*?(?=##|\Z)'
        }
        
        sections = []
        
        for section_name, pattern in section_patterns.items():
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                section_content = match.group(0).strip()
                if len(section_content) > 50:  # Only include substantial sections
                    section_metadata = metadata.copy()
                    section_metadata.update({
                        'section_name': section_name,
                        'section_type': section_name
                    })
                    
                    sections.append(Document(
                        page_content=section_content,
                        metadata=section_metadata
                    ))
        
        if not sections:
            regular_chunks = self.text_splitter.split_documents([document])
            for chunk in regular_chunks:
                chunk.metadata.update(metadata)
            return regular_chunks
        
        full_doc = Document(
            page_content=content,
            metadata={**metadata, 'section_name': 'full_document', 'section_type': 'complete'}
        )
        sections.append(full_doc)
        
        return sections
    
    def _extract_patient_id(self, content: str) -> Optional[str]:
        """Extract patient ID from content"""
        patterns = [
            r'\*\*Patient ID:\*\*\s*([^\n\*]+)',
            r'Patient ID:\s*([^\n]+)',
            r'Patient ID\*\*:\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_document_type(self, content: str) -> Optional[str]:
        """Extract document type from content"""
        content_lower = content.lower()
        
        if 'discharge summary' in content_lower:
            return 'discharge_summary'
        elif 'lab report' in content_lower:
            return 'lab_report'
        elif 'clinical note' in content_lower:
            return 'clinical_note'
        elif 'consultation' in content_lower:
            return 'consultation'
        else:
            return 'medical_document'
    
    def _extract_diagnoses(self, content: str) -> List[str]:
        """Extract diagnoses and ICD codes from content"""
        diagnoses = []
        
        diag_match = re.search(r'## Diagnosis.*?(?=##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if diag_match:
            diag_content = diag_match.group(0)
            
            icd_patterns = [
                r'\*\*([A-Z]\d+\.?\d*)\*\*:\s*([^\n\*]+)',
                r'([A-Z]\d+\.?\d*):\s*([^\n]+)',
                r'\*([A-Z]\d+\.?\d*)\*:\s*([^\n\*]+)'
            ]
            
            for pattern in icd_patterns:
                matches = re.findall(pattern, diag_content)
                for code, desc in matches:
                    diagnoses.append(f"{code}: {desc.strip()}")
            
            conditions = [
                'myocardial infarction', 'heart attack', 'stemi', 'nstemi',
                'hypertension', 'diabetes', 'copd', 'pneumonia', 'stroke'
            ]
            
            for condition in conditions:
                if condition in content.lower():
                    diagnoses.append(condition)
        
        return list(set(diagnoses))  # Remove duplicates
    
    def _expand_medical_query(self, query: str) -> str:
        """Expand medical queries with synonyms and related terms"""
        query_lower = query.lower()
        
        expansions = {
            'heart attack': ['heart attack', 'myocardial infarction', 'MI', 'STEMI', 'NSTEMI', 'cardiac arrest', 'coronary event'],
            'myocardial infarction': ['myocardial infarction', 'heart attack', 'MI', 'STEMI', 'NSTEMI'],
            'high blood pressure': ['high blood pressure', 'hypertension', 'HTN', 'elevated BP'],
            'diabetes': ['diabetes', 'diabetic', 'DM', 'type 2 diabetes', 'T2DM', 'glucose'],
            'medication': ['medication', 'drug', 'prescription', 'medicine', 'pharmaceutical'],
            'treatment': ['treatment', 'therapy', 'intervention', 'management', 'care plan'],
            'chest pain': ['chest pain', 'chest discomfort', 'substernal pain', 'cardiac pain'],
            'blood thinner': ['blood thinner', 'anticoagulant', 'aspirin', 'clopidogrel', 'warfarin']
        }
        
        expanded_terms = []
        for term, synonyms in expansions.items():
            if term in query_lower:
                expanded_terms.extend(synonyms)
        
        if expanded_terms:
            expanded_query = f"{query} {' '.join(set(expanded_terms))}"
            return expanded_query
        
        return query
    
    def process_documents(self, force_reprocess: bool = False) -> Dict[str, Any]:
        """Process documents and add to vector store"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}
        
        # Check if documents already exis
        try:
            existing_count = self.vector_store._collection.count()
            if existing_count > 0 and not force_reprocess:
                return {
                    "status": "already_processed",
                    "total_documents": existing_count
                }
        except:
            pass
        
        try:
            loader = DirectoryLoader(
                str(self.docs_path),
                glob="**/*.md",
                loader_cls=UnstructuredMarkdownLoader
            )
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents")
            
            if not documents:
                return {"error": "No documents found to process"}
            
            all_sections = []
            for doc in documents:
                sections = self._extract_medical_sections(doc)
                all_sections.extend(sections)
            
            logger.info(f"Extracted {len(all_sections)} medical sections from {len(documents)} documents")
            
            if force_reprocess:
                try:
                    self.vector_store._collection.delete(where={})
                except:
                    pass
            
            batch_size = 100
            for i in range(0, len(all_sections), batch_size):
                batch = all_sections[i:i+batch_size]
                self.vector_store.add_documents(batch)
                logger.info(f"Added batch {i//batch_size + 1}/{(len(all_sections) + batch_size - 1)//batch_size}")
            
            self.rag_chain = self._create_rag_chain()
            
            return {
                "status": "completed",
                "documents_processed": len(documents),
                "total_chunks": len(all_sections)
            }
            
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            return {"error": str(e)}
    
    def search_documents(self, 
                        query: str, 
                        n_results: int = 5,
                        use_llm: bool = True) -> Dict[str, Any]:
        """Search documents with optional LLM processing"""
        if not self.vector_store:
            return {"error": "Documents not processed yet. Please run process_documents() first."}
        
        try:
            expanded_query = self._expand_medical_query(query)
            search_query = expanded_query if expanded_query != query else query
            
            if use_llm and self.rag_chain:
                answer = self.rag_chain.invoke(query)
                
                retriever = self.vector_store.as_retriever(search_kwargs={"k": n_results})
                source_docs = retriever.invoke(search_query)
                
                return {
                    "query": query,
                    "answer": answer,
                    "sources": [
                        {
                            "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                            "metadata": doc.metadata
                        }
                        for doc in source_docs
                    ]
                }
            else:
                docs = self.vector_store.similarity_search(search_query, k=n_results)
                
                return {
                    "query": query,
                    "results": [
                        {
                            "content": doc.page_content,
                            "metadata": doc.metadata
                        }
                        for doc in docs
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the document collection"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}
        
        try:
            count = self.vector_store._collection.count()
            return {
                "total_chunks": count,
                "llm_configured": self.llm is not None,
                "rag_chain_available": self.rag_chain is not None
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}