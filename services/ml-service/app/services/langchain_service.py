import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
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
        
        # Initialize components
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
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
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_template("""
You are a medical assistant analyzing clinical documents. Use the following context to answer the question.
If you don't know the answer based on the context, say so. Don't make up information.

Context: {context}

Question: {question}

Answer:""")
        
        # Create the RAG chain using LCEL
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
    
    def process_documents(self, force_reprocess: bool = False) -> Dict[str, Any]:
        """Process documents and add to vector store"""
        if not self.vector_store:
            return {"error": "Vector store not initialized"}
        
        # Check if documents already exist
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
            
            split_documents = self.text_splitter.split_documents(documents)
            logger.info(f"Split into {len(split_documents)} chunks")
            
            if force_reprocess:
                try:
                    self.vector_store._collection.delete(where={})
                except:
                    pass
            
            batch_size = 100
            for i in range(0, len(split_documents), batch_size):
                batch = split_documents[i:i+batch_size]
                self.vector_store.add_documents(batch)
                logger.info(f"Added batch {i//batch_size + 1}/{(len(split_documents) + batch_size - 1)//batch_size}")
            
            self.rag_chain = self._create_rag_chain()
            
            return {
                "status": "completed",
                "documents_processed": len(documents),
                "total_chunks": len(split_documents)
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
            if use_llm and self.rag_chain:
                answer = self.rag_chain.invoke(query)
                
                retriever = self.vector_store.as_retriever(search_kwargs={"k": n_results})
                source_docs = retriever.invoke(query)
                
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
                docs = self.vector_store.similarity_search(query, k=n_results)
                
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