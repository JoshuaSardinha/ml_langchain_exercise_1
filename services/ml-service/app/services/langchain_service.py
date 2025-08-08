import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from langchain_community.document_loaders import UnstructuredMarkdownLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate

# LLM imports - we'll try multiple providers
try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    ChatGoogleGenerativeAI = None

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


class LangChainDocumentService:
    """Enhanced document service using LangChain for better RAG capabilities"""
    
    def __init__(self, 
                 docs_path: str = "data/docs",
                 vectordb_path: str = "data/vectordb_langchain",
                 embedding_model: str = None,
                 collection_name: str = "medical_documents_langchain"):
        
        self.docs_path = Path(docs_path)
        self.vectordb_path = Path(vectordb_path)
        self.collection_name = collection_name
        
        # Use environment variable or default
        self.embedding_model_name = embedding_model or os.getenv(
            "EMBEDDING_MODEL", 
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize components
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = None
        self.llm = None
        self.memory = None
        self.qa_chain = None
        self.conversational_chain = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all LangChain components"""
        try:
            # Initialize embeddings
            logger.info(f"Initializing embeddings with {self.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=int(os.getenv("CHUNK_SIZE", 500)),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 50)),
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
            )
            
            # Initialize LLM
            self._initialize_llm()
            
            # Initialize memory
            self._initialize_memory()
            
            # Initialize vector store
            self._initialize_vector_store()
            
            logger.info("LangChain components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing LangChain components: {e}")
            raise
    
    def _initialize_llm(self):
        """Initialize the Large Language Model based on available API keys"""
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        
        try:
            if openai_key and OPENAI_AVAILABLE:
                logger.info("Initializing OpenAI LLM...")
                self.llm = ChatOpenAI(
                    api_key=openai_key,
                    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                    temperature=0.7,
                    max_tokens=2000
                )
                logger.info(f"✅ OpenAI LLM initialized successfully: {type(self.llm).__name__}")
            elif google_key and GEMINI_AVAILABLE:
                logger.info("Using Google Gemini LLM")
                self.llm = ChatGoogleGenerativeAI(
                    google_api_key=google_key,
                    model=os.getenv("GEMINI_MODEL", "gemini-pro"),
                    temperature=0.7,
                    max_output_tokens=2000
                )
            elif anthropic_key and ANTHROPIC_AVAILABLE:
                logger.info("Using Anthropic Claude LLM")
                self.llm = ChatAnthropic(
                    anthropic_api_key=anthropic_key,
                    model=os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229"),
                    temperature=0.7,
                    max_tokens=2000
                )
            else:
                logger.warning(f"No LLM configured - OpenAI: key={bool(openai_key)}/available={OPENAI_AVAILABLE}, Google: {bool(google_key)}/{GEMINI_AVAILABLE}, Anthropic: {bool(anthropic_key)}/{ANTHROPIC_AVAILABLE}")
                self.llm = None
        except Exception as e:
            logger.error(f"LLM initialization failed with exception: {e}")
            self.llm = None
    
    def _initialize_memory(self):
        """Initialize conversation memory"""
        if self.llm:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
    
    def _initialize_vector_store(self):
        """Initialize or load the vector store"""
        self.vectordb_path.mkdir(parents=True, exist_ok=True)
        
        # Check if vector store already exists
        chroma_path = self.vectordb_path / self.collection_name
        
        if chroma_path.exists() and any(chroma_path.iterdir()):
            logger.info(f"Loading existing vector store from {chroma_path}")
            self.vector_store = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
        else:
            logger.info("Creating new vector store")
            self.vector_store = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
    
    def process_documents(self, force_reprocess: bool = False) -> Dict[str, Any]:
        """Process documents using LangChain document loaders and splitters"""
        
        # Check if already processed
        if self.vector_store and self.vector_store._collection.count() > 0 and not force_reprocess:
            logger.info("Documents already processed. Use force_reprocess=True to reprocess.")
            return {
                "status": "already_processed",
                "total_documents": self.vector_store._collection.count()
            }
        
        logger.info("Starting document processing with LangChain...")
        
        # Use DirectoryLoader to load all markdown files
        loader = DirectoryLoader(
            str(self.docs_path),
            glob="**/*.md",
            loader_cls=UnstructuredMarkdownLoader,
            show_progress=True
        )
        
        try:
            # Load all documents
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents")
            
            # Enrich metadata
            for doc in documents:
                self._enrich_document_metadata(doc)
            
            # Split documents into chunks
            split_documents = self.text_splitter.split_documents(documents)
            logger.info(f"Created {len(split_documents)} chunks")
            
            # Add to vector store
            if force_reprocess and self.vector_store:
                # Clear existing data
                self.vector_store._collection.delete(where={})
            
            # Add documents in batches
            batch_size = 100
            for i in range(0, len(split_documents), batch_size):
                batch = split_documents[i:i+batch_size]
                self.vector_store.add_documents(batch)
                logger.info(f"Added batch {i//batch_size + 1}/{(len(split_documents) + batch_size - 1)//batch_size}")
            
            # Persist the vector store
            self.vector_store.persist()
            
            # Initialize retrieval chains after processing
            self._initialize_retrieval_chains()
            
            return {
                "status": "completed",
                "documents_processed": len(documents),
                "total_chunks": len(split_documents),
                "collection_size": self.vector_store._collection.count()
            }
            
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            return {"error": str(e)}
    
    def _enrich_document_metadata(self, doc: Document):
        """Enrich document metadata with extracted information"""
        content = doc.page_content
        filename = Path(doc.metadata.get("source", "")).name
        
        # Extract and add metadata
        doc.metadata.update({
            "document_id": filename.replace('.md', ''),
            "filename": filename,
            "document_type": self._infer_document_type(content),
            "patient_id": self._extract_patient_id(content),
            "date_created": self._extract_date(content),
            "medications": self._extract_medications(content),
            "diagnosis_codes": self._extract_diagnosis_codes(content)
        })
    
    def _infer_document_type(self, content: str) -> str:
        """Infer document type from content"""
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
    
    def _extract_patient_id(self, content: str) -> Optional[str]:
        """Extract patient ID from document"""
        import re
        patterns = [
            r'\*\*Patient ID:\*\* ([^\n\*]+)',
            r'Patient ID: ([^\n\*]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """Extract date from document"""
        import re
        patterns = [
            r'\*\*Date Created:\*\* ([\d\-\/]+)',
            r'Date Created: ([\d\-\/]+)',
            r'Date: ([\d\-\/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_medications(self, content: str) -> List[str]:
        """Extract medications from document"""
        import re
        medications = []
        
        med_section_match = re.search(
            r'## Medications(.*?)(?=##|$)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if med_section_match:
            med_section = med_section_match.group(1)
            patterns = [
                r'\*\*([A-Za-z\-/]+):\*\*',
                r'\* ([A-Za-z\-/]+):',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, med_section, re.IGNORECASE)
                medications.extend(matches)
        
        return list(set(medications))
    
    def _extract_diagnosis_codes(self, content: str) -> List[str]:
        """Extract diagnosis codes from document"""
        import re
        codes = []
        patterns = [
            r'Code:\*\* ([A-Z]\d+\.?\d*)',
            r'Code: ([A-Z]\d+\.?\d*)',
            r'\b([A-Z]\d{2,3}\.?\d*)\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            codes.extend(matches)
        
        return list(set(codes))
    
    def _initialize_retrieval_chains(self):
        """Initialize various retrieval chains for different use cases"""
        if not self.vector_store:
            logger.warning("Vector store not initialized. Cannot create retrieval chains.")
            return
        
        # Create base retriever
        base_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        # Create multi-query retriever for better coverage
        if self.llm:
            self.multi_query_retriever = MultiQueryRetriever.from_llm(
                retriever=base_retriever,
                llm=self.llm
            )
            
            # Create QA chain for direct question answering
            qa_prompt = PromptTemplate(
                template="""You are a medical assistant analyzing clinical documents. 
                Use the following pieces of context to answer the question at the end.
                If you don't know the answer, say so. Don't make up information.
                Always cite the document source when providing information.
                
                Context: {context}
                
                Question: {question}
                
                Answer: """,
                input_variables=["context", "question"]
            )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.multi_query_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": qa_prompt}
            )
            
            # Create conversational chain for multi-turn conversations
            if self.memory:
                self.conversational_chain = ConversationalRetrievalChain.from_llm(
                    llm=self.llm,
                    retriever=self.multi_query_retriever,
                    memory=self.memory,
                    return_source_documents=True,
                    verbose=True
                )
        else:
            self.multi_query_retriever = base_retriever
            logger.warning("LLM not available. Using basic retriever only.")
    
    def search_documents(self, 
                        query: str, 
                        n_results: int = 5,
                        use_llm: bool = True,
                        include_sources: bool = True) -> Dict[str, Any]:
        """Enhanced document search using LangChain"""
        
        if not self.vector_store:
            return {"error": "Documents not processed yet. Please run process_documents() first."}
        
        try:
            if use_llm and self.qa_chain:
                # Use QA chain for intelligent answering
                result = self.qa_chain({"query": query})
                
                response = {
                    "query": query,
                    "answer": result["result"],
                    "sources": []
                }
                
                if include_sources and "source_documents" in result:
                    for doc in result["source_documents"]:
                        response["sources"].append({
                            "content": doc.page_content[:500],  # Truncate for display
                            "metadata": doc.metadata,
                            "citation": self._format_citation(doc.metadata)
                        })
                
                return response
            else:
                # Fallback to similarity search
                docs = self.vector_store.similarity_search(query, k=n_results)
                
                results = []
                for doc in docs:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "citation": self._format_citation(doc.metadata)
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }
                
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"error": str(e)}
    
    def chat(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle conversational interactions with memory"""
        
        if not self.conversational_chain:
            return {"error": "Conversational chain not initialized. Please ensure LLM is configured."}
        
        try:
            # Get response from conversational chain
            result = self.conversational_chain({"question": message})
            
            response = {
                "question": message,
                "answer": result["answer"],
                "session_id": session_id,
                "sources": []
            }
            
            # Add source documents if available
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    response["sources"].append({
                        "content": doc.page_content[:500],
                        "metadata": doc.metadata,
                        "citation": self._format_citation(doc.metadata)
                    })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {"error": str(e)}
    
    def _format_citation(self, metadata: Dict[str, Any]) -> str:
        """Format citation information for a result"""
        citation_parts = []
        
        if metadata.get('filename'):
            citation_parts.append(f"Document: {metadata['filename']}")
        
        if metadata.get('document_type'):
            doc_type = metadata['document_type'].replace('_', ' ').title()
            citation_parts.append(f"Type: {doc_type}")
        
        if metadata.get('date_created'):
            citation_parts.append(f"Date: {metadata['date_created']}")
        
        if metadata.get('patient_id'):
            citation_parts.append(f"Patient: {metadata['patient_id']}")
        
        return " | ".join(citation_parts)
    
    def clear_memory(self, session_id: Optional[str] = None):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()
            logger.info(f"Cleared memory for session: {session_id or 'default'}")
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get current memory state"""
        if self.memory:
            return self.memory.load_memory_variables({})
        return {}
    
    def create_hybrid_retriever(self) -> EnsembleRetriever:
        """Create a hybrid retriever combining keyword and semantic search"""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        
        # Get all documents for BM25
        all_docs = self.vector_store.get()
        documents = [
            Document(page_content=doc, metadata=meta) 
            for doc, meta in zip(all_docs['documents'], all_docs['metadatas'])
        ]
        
        # Create BM25 retriever for keyword search
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = 5
        
        # Create semantic retriever
        semantic_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        
        # Combine them with equal weights
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, semantic_retriever],
            weights=[0.5, 0.5]
        )
        
        return ensemble_retriever
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}
        
        try:
            collection_count = self.vector_store._collection.count()
            
            # Get sample of documents to analyze
            sample = self.vector_store.get(limit=100)
            
            doc_types = {}
            unique_patients = set()
            unique_documents = set()
            
            for metadata in sample.get('metadatas', []):
                # Count document types
                doc_type = metadata.get('document_type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                # Track unique patients and documents
                if metadata.get('patient_id'):
                    unique_patients.add(metadata['patient_id'])
                if metadata.get('document_id'):
                    unique_documents.add(metadata['document_id'])
            
            return {
                "total_chunks": collection_count,
                "sample_size": len(sample.get('metadatas', [])),
                "document_types": doc_types,
                "unique_patients_in_sample": len(unique_patients),
                "unique_documents_in_sample": len(unique_documents),
                "llm_configured": self.llm is not None,
                "llm_type": type(self.llm).__name__ if self.llm else None,
                "memory_enabled": self.memory is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}