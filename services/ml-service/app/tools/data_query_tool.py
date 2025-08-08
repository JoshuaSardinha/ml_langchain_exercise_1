import pandas as pd
import logging
import re
from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DataQueryInput(BaseModel):
    """Input schema for DataQueryTool"""
    query: str = Field(description="Natural language query about patient data")
    return_type: str = Field(
        default="summary",
        description="Type of return: 'summary', 'dataframe', 'count', 'list'"
    )


class DataQueryTool(BaseTool):
    """Tool for querying patient data using natural language"""
    
    name: str = "data_query"
    description: str = """Useful for answering questions about patient data statistics, counts, and demographics."""
    args_schema: type = DataQueryInput
    data_service: Optional[Any] = None
    _df: Optional[Any] = None
    
    def __init__(self, data_service=None, **kwargs):
        super().__init__(data_service=data_service, **kwargs)
        self._df = None
    
    @property
    def df(self):
        """Lazy load the dataframe"""
        if self._df is None and self.data_service:
            self._df = self.data_service.get_dataframe()
        return self._df
    
    def _run(
        self,
        query: str,
        return_type: str = "summary",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute the data query"""
        try:
            if self.df is None:
                return "Error: Patient data not loaded"
            
            result = self._parse_and_execute_query(query, return_type)
            
            return self._format_result(result, return_type)
            
        except Exception as e:
            logger.error(f"Error executing data query: {e}")
            return f"Error executing query: {str(e)}"
    
    async def _arun(self, *args, **kwargs):
        """Async version not implemented"""
        raise NotImplementedError("DataQueryTool does not support async")
    
    def _parse_and_execute_query(self, query: str, return_type: str) -> Any:
        """Parse natural language query and execute pandas operations"""
        query_lower = query.lower()
        
        if "how many" in query_lower or "count" in query_lower:
            return self._handle_count_query(query_lower)
        elif "average" in query_lower or "mean" in query_lower:
            return self._handle_average_query(query_lower)
        elif "list" in query_lower or "show" in query_lower:
            return self._handle_list_query(query_lower)
        elif "compare" in query_lower:
            return self._handle_comparison_query(query_lower)
        else:
            return self._handle_general_query(query_lower)
    
    def _handle_count_query(self, query: str) -> Dict[str, Any]:
        """Handle count-based queries"""
        df = self.df
        
        if "smoker" in query:
            if "non" in query or "not" in query:
                count = len(df[df['smoker'] == 'No'])
                total = len(df)
                return {
                    "count": count,
                    "percentage": (count / total) * 100,
                    "total": total,
                    "description": "non-smokers in the dataset"
                }
            else:
                count = len(df[df['smoker'] == 'Yes'])
                total = len(df)
                return {
                    "count": count,
                    "percentage": (count / total) * 100,
                    "total": total,
                    "description": "smokers in the dataset"
                }
        
        elif "male" in query and "40" in query and "readmitted" in query:
            filtered = df[(df['sex'] == 'Male') & (df['age'] > 40) & (df['readmitted'] == 1)]
            return {
                "count": len(filtered),
                "total_males_over_40": len(df[(df['sex'] == 'Male') & (df['age'] > 40)]),
                "description": "males older than 40 who were readmitted"
            }
        
        elif "medication" in query:
            match = re.search(r'(\d+)\s*medication', query)
            if match:
                threshold = int(match.group(1))
                if "more than" in query or ">" in query:
                    filtered = df[df['medication_count'] > threshold]
                elif "less than" in query or "<" in query:
                    filtered = df[df['medication_count'] < threshold]
                else:
                    filtered = df[df['medication_count'] == threshold]
                
                return {
                    "count": len(filtered),
                    "percentage": (len(filtered) / len(df)) * 100,
                    "description": f"patients with medication count criteria"
                }
        
        return {"count": len(df), "description": "total patients in dataset"}
    
    def _handle_average_query(self, query: str) -> Dict[str, Any]:
        """Handle average/mean queries"""
        df = self.df
        
        if "bmi" in query:
            if "copd" in query or "chronic_obstructive" in query:
                copd_patients = df[df['chronic_obstructive_pulmonary_disease'].notna()]
                return {
                    "average": copd_patients['bmi'].mean(),
                    "std": copd_patients['bmi'].std(),
                    "count": len(copd_patients),
                    "description": "average BMI of COPD patients"
                }
            else:
                return {
                    "average": df['bmi'].mean(),
                    "std": df['bmi'].std(),
                    "description": "average BMI of all patients"
                }
        
        elif "age" in query:
            return {
                "average": df['age'].mean(),
                "std": df['age'].std(),
                "description": "average age of patients"
            }
        
        elif "medication" in query:
            return {
                "average": df['medication_count'].mean(),
                "std": df['medication_count'].std(),
                "description": "average medication count"
            }
        
        return {"error": "Could not determine what to average"}
    
    def _handle_list_query(self, query: str) -> Dict[str, Any]:
        """Handle list/show queries"""
        df = self.df
        
        if "patient" in query:
            sample = df.head(10)
            return {
                "data": sample.to_dict('records'),
                "count": len(sample),
                "description": "sample of patients"
            }
        
        return {"data": [], "description": "no data to list"}
    
    def _handle_comparison_query(self, query: str) -> Dict[str, Any]:
        """Handle comparison queries"""
        df = self.df
        
        if "readmitted" in query and ("lab" in query or "result" in query):
            readmitted = df[df['readmitted'] == 1]
            not_readmitted = df[df['readmitted'] == 0]
            
            comparison = {
                "readmitted": {
                    "mean_alt": readmitted['alanine_aminotransferase'].mean(),
                    "std_alt": readmitted['alanine_aminotransferase'].std(),
                    "count": len(readmitted)
                },
                "not_readmitted": {
                    "mean_alt": not_readmitted['alanine_aminotransferase'].mean(),
                    "std_alt": not_readmitted['alanine_aminotransferase'].std(),
                    "count": len(not_readmitted)
                },
                "description": "ALT levels comparison between readmitted and non-readmitted patients"
            }
            return comparison
        
        return {"error": "Could not perform comparison"}
    
    def _handle_general_query(self, query: str) -> Dict[str, Any]:
        """Handle general queries"""
        df = self.df
        
        return {
            "total_patients": len(df),
            "columns": list(df.columns),
            "description": "general dataset information"
        }
    
    def _format_result(self, result: Any, return_type: str) -> str:
        """Format the result based on return type"""
        if isinstance(result, dict):
            if "error" in result:
                return result["error"]
            
            if "count" in result:
                response = f"Found {result['count']} {result.get('description', 'records')}"
                if "percentage" in result:
                    response += f" ({result['percentage']:.1f}% of total)"
                if "total" in result and "count" in result:
                    response += f" out of {result['total']} total"
                return response
            
            if "average" in result:
                response = f"The {result.get('description', 'average')} is {result['average']:.2f}"
                if "std" in result:
                    response += f" (std: {result['std']:.2f})"
                return response
            
            if "data" in result:
                return f"Found {result.get('count', len(result['data']))} {result.get('description', 'items')}"
            
            if "readmitted" in result and "not_readmitted" in result:
                return self._format_comparison(result)
            
            return str(result)
        
        return str(result)
    
    def _format_comparison(self, comparison: Dict) -> str:
        """Format comparison results"""
        desc = comparison.get('description', 'Comparison')
        readmitted = comparison['readmitted']
        not_readmitted = comparison['not_readmitted']
        
        response = f"{desc}:\n"
        response += f"- Readmitted patients (n={readmitted['count']}): "
        response += f"Mean ALT = {readmitted['mean_alt']:.2f} (std: {readmitted['std_alt']:.2f})\n"
        response += f"- Non-readmitted patients (n={not_readmitted['count']}): "
        response += f"Mean ALT = {not_readmitted['mean_alt']:.2f} (std: {not_readmitted['std_alt']:.2f})"
        
        return response