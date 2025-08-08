import logging
import json
from typing import Dict, Any, Optional, List
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VisualizationInput(BaseModel):
    """Input schema for VisualizationTool"""
    chart_type: str = Field(
        description="Type of chart: 'bar', 'line', 'pie', 'histogram', 'scatter', 'box'"
    )
    data_query: str = Field(
        description="Description of what data to visualize"
    )
    x_axis: Optional[str] = Field(
        default=None,
        description="X-axis variable (for scatter, line charts)"
    )
    y_axis: Optional[str] = Field(
        default=None,
        description="Y-axis variable (for scatter, line charts)"
    )
    group_by: Optional[str] = Field(
        default=None,
        description="Variable to group/color by"
    )
    title: Optional[str] = Field(
        default=None,
        description="Chart title"
    )


class VisualizationTool(BaseTool):
    """Tool for creating data visualizations and charts"""
    
    name: str = "visualization"
    description: str = """Useful for creating charts and visualizations from patient data."""
    args_schema: type = VisualizationInput
    data_service: Optional[Any] = None
    
    def __init__(self, data_service=None, **kwargs):
        super().__init__(data_service=data_service, **kwargs)
    
    def _run(
        self,
        chart_type: str,
        data_query: str,
        x_axis: Optional[str] = None,
        y_axis: Optional[str] = None,
        group_by: Optional[str] = None,
        title: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Create a visualization specification"""
        try:
            if not self.data_service:
                return "Error: Data service not initialized"
            
            df = self.data_service.get_dataframe() if hasattr(self.data_service, 'get_dataframe') else None
            if df is None:
                return "Error: Could not access patient data"
            
            chart_spec = self._generate_chart_spec(
                df=df,
                chart_type=chart_type.lower(),
                data_query=data_query,
                x_axis=x_axis,
                y_axis=y_axis,
                group_by=group_by,
                title=title
            )
            
            return self._format_chart_response(chart_spec)
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return f"Error creating visualization: {str(e)}"
    
    async def _arun(self, *args, **kwargs):
        """Async version not implemented"""
        raise NotImplementedError("VisualizationTool does not support async")
    
    def _generate_chart_spec(self, df, chart_type: str, data_query: str, **kwargs) -> Dict[str, Any]:
        """Generate chart specification based on the query"""
        
        query_lower = data_query.lower()
        
        if chart_type == "bar":
            return self._create_bar_chart(df, query_lower, **kwargs)
        elif chart_type == "pie":
            return self._create_pie_chart(df, query_lower, **kwargs)
        elif chart_type == "histogram":
            return self._create_histogram(df, query_lower, **kwargs)
        elif chart_type == "scatter":
            return self._create_scatter_plot(df, query_lower, **kwargs)
        elif chart_type == "box":
            return self._create_box_plot(df, query_lower, **kwargs)
        elif chart_type == "line":
            return self._create_line_chart(df, query_lower, **kwargs)
        else:
            return {"error": f"Unsupported chart type: {chart_type}"}
    
    def _create_bar_chart(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create bar chart specification"""
        
        if "smoker" in query:
            data = df['smoker'].value_counts()
            chart_spec = {
                "type": "bar",
                "data": {
                    "labels": ["Non-smoker", "Smoker"],
                    "values": [data.get(False, 0), data.get(True, 0)]
                },
                "title": kwargs.get("title", "Smoking Status Distribution"),
                "x_label": "Smoking Status",
                "y_label": "Number of Patients"
            }
        elif "sex" in query or "gender" in query:
            data = df['sex'].value_counts()
            chart_spec = {
                "type": "bar",
                "data": {
                    "labels": list(data.index),
                    "values": list(data.values)
                },
                "title": kwargs.get("title", "Gender Distribution"),
                "x_label": "Gender",
                "y_label": "Number of Patients"
            }
        elif "copd" in query or "chronic_obstructive" in query:
            copd_col = 'chronic_obstructive_pulmonary_disease'
            if copd_col in df.columns:
                data = df[copd_col].value_counts().sort_index()
                chart_spec = {
                    "type": "bar",
                    "data": {
                        "labels": list(data.index),
                        "values": list(data.values)
                    },
                    "title": kwargs.get("title", "COPD Classification Distribution"),
                    "x_label": "COPD Class",
                    "y_label": "Number of Patients"
                }
            else:
                return {"error": "COPD column not found in dataset"}
        elif "readmitted" in query or "readmission" in query:
            data = df['readmitted'].value_counts()
            chart_spec = {
                "type": "bar",
                "data": {
                    "labels": ["Not Readmitted", "Readmitted"],
                    "values": [data.get(False, 0), data.get(True, 0)]
                },
                "title": kwargs.get("title", "Readmission Status"),
                "x_label": "Readmission",
                "y_label": "Number of Patients"
            }
        else:
            chart_spec = {
                "type": "bar",
                "data": {"labels": [], "values": []},
                "title": "Bar Chart",
                "error": f"Could not determine what to visualize from: {query}"
            }
        
        return chart_spec
    
    def _create_pie_chart(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create pie chart specification"""
        
        if "copd" in query:
            copd_col = 'chronic_obstructive_pulmonary_disease'
            if copd_col in df.columns:
                data = df[copd_col].value_counts()
                chart_spec = {
                    "type": "pie",
                    "data": {
                        "labels": list(data.index),
                        "values": list(data.values)
                    },
                    "title": kwargs.get("title", "COPD Classifications Distribution")
                }
            else:
                return {"error": "COPD column not found"}
        elif "exercise" in query:
            data = df['exercise_frequency'].value_counts()
            chart_spec = {
                "type": "pie",
                "data": {
                    "labels": list(data.index),
                    "values": list(data.values)
                },
                "title": kwargs.get("title", "Exercise Frequency Distribution")
            }
        else:
            chart_spec = {
                "type": "pie",
                "data": {"labels": [], "values": []},
                "error": f"Could not determine what to visualize from: {query}"
            }
        
        return chart_spec
    
    def _create_histogram(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create histogram specification"""
        
        if "age" in query:
            data = df['age'].dropna()
            chart_spec = {
                "type": "histogram",
                "data": {
                    "values": list(data),
                    "bins": 20
                },
                "title": kwargs.get("title", "Age Distribution"),
                "x_label": "Age",
                "y_label": "Frequency",
                "statistics": {
                    "mean": float(data.mean()),
                    "std": float(data.std()),
                    "median": float(data.median())
                }
            }
        elif "bmi" in query:
            data = df['bmi'].dropna()
            chart_spec = {
                "type": "histogram",
                "data": {
                    "values": list(data),
                    "bins": 25
                },
                "title": kwargs.get("title", "BMI Distribution"),
                "x_label": "BMI",
                "y_label": "Frequency",
                "statistics": {
                    "mean": float(data.mean()),
                    "std": float(data.std()),
                    "median": float(data.median())
                }
            }
        elif "alt" in query or "alanine" in query:
            data = df['alanine_aminotransferase'].dropna()
            chart_spec = {
                "type": "histogram",
                "data": {
                    "values": list(data),
                    "bins": 30
                },
                "title": kwargs.get("title", "ALT Levels Distribution"),
                "x_label": "ALT (U/L)",
                "y_label": "Frequency",
                "statistics": {
                    "mean": float(data.mean()),
                    "std": float(data.std()),
                    "median": float(data.median())
                }
            }
        else:
            chart_spec = {
                "type": "histogram",
                "data": {"values": []},
                "error": f"Could not determine what to visualize from: {query}"
            }
        
        return chart_spec
    
    def _create_scatter_plot(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create scatter plot specification"""
        
        x_axis = kwargs.get('x_axis')
        y_axis = kwargs.get('y_axis')
        
        if not x_axis or not y_axis:
            if "bmi" in query and "alt" in query:
                x_axis, y_axis = "bmi", "alanine_aminotransferase"
            elif "age" in query and "alt" in query:
                x_axis, y_axis = "age", "alanine_aminotransferase"
            elif "age" in query and "bmi" in query:
                x_axis, y_axis = "age", "bmi"
            else:
                return {"error": "Could not determine x and y variables for scatter plot"}
        
        if x_axis not in df.columns or y_axis not in df.columns:
            return {"error": f"Columns {x_axis} or {y_axis} not found in data"}
        
        plot_data = df[[x_axis, y_axis]].dropna()
        
        chart_spec = {
            "type": "scatter",
            "data": {
                "x": list(plot_data[x_axis]),
                "y": list(plot_data[y_axis])
            },
            "title": kwargs.get("title", f"{y_axis} vs {x_axis}"),
            "x_label": x_axis.replace('_', ' ').title(),
            "y_label": y_axis.replace('_', ' ').title(),
            "correlation": float(plot_data[x_axis].corr(plot_data[y_axis]))
        }
        
        group_by = kwargs.get('group_by')
        if group_by and group_by in df.columns:
            chart_spec["group_by"] = group_by
            chart_spec["data"]["groups"] = list(plot_data[group_by])
        
        return chart_spec
    
    def _create_box_plot(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create box plot specification"""
        
        if "alt" in query and "readmitted" in query:
            chart_spec = {
                "type": "box",
                "data": {
                    "values": list(df['alanine_aminotransferase'].dropna()),
                    "groups": list(df['readmitted'].dropna()),
                    "group_names": ["Not Readmitted", "Readmitted"]
                },
                "title": kwargs.get("title", "ALT Levels by Readmission Status"),
                "x_label": "Readmission Status",
                "y_label": "ALT (U/L)"
            }
        elif "bmi" in query and "copd" in query:
            copd_col = 'chronic_obstructive_pulmonary_disease'
            if copd_col in df.columns:
                chart_spec = {
                    "type": "box",
                    "data": {
                        "values": list(df['bmi'].dropna()),
                        "groups": list(df[copd_col].dropna())
                    },
                    "title": kwargs.get("title", "BMI by COPD Classification"),
                    "x_label": "COPD Class",
                    "y_label": "BMI"
                }
            else:
                return {"error": "COPD column not found"}
        else:
            chart_spec = {
                "type": "box",
                "data": {},
                "error": f"Could not determine what to visualize from: {query}"
            }
        
        return chart_spec
    
    def _create_line_chart(self, df, query: str, **kwargs) -> Dict[str, Any]:
        """Create line chart specification"""
        
        chart_spec = {
            "type": "line",
            "data": {},
            "error": "Line charts require temporal data which is not available in this dataset"
        }
        
        return chart_spec
    
    def _format_chart_response(self, chart_spec: Dict[str, Any]) -> str:
        """Format the chart specification as a response"""
        
        if "error" in chart_spec:
            return f"Visualization Error: {chart_spec['error']}"
        
        chart_type = chart_spec.get("type", "chart")
        title = chart_spec.get("title", "Chart")
        
        response = f"Created {chart_type} chart: '{title}'\n\n"
        
        response += "Chart Configuration:\n"
        response += json.dumps(chart_spec, indent=2)
        
        if "statistics" in chart_spec:
            stats = chart_spec["statistics"]
            response += f"\n\nSummary Statistics:\n"
            response += f"- Mean: {stats.get('mean', 'N/A'):.2f}\n"
            response += f"- Median: {stats.get('median', 'N/A'):.2f}\n"
            response += f"- Std Dev: {stats.get('std', 'N/A'):.2f}\n"
        
        if "correlation" in chart_spec:
            corr = chart_spec["correlation"]
            response += f"\nCorrelation Coefficient: {corr:.3f}\n"
            if abs(corr) > 0.7:
                response += "Strong correlation detected!\n"
            elif abs(corr) > 0.3:
                response += "Moderate correlation detected.\n"
            else:
                response += "Weak or no correlation.\n"
        
        return response
    
    def suggest_visualizations(self, data_query: str) -> str:
        """Suggest appropriate visualizations for a given query"""
        query_lower = data_query.lower()
        suggestions = []
        
        if any(word in query_lower for word in ["distribution", "histogram", "age", "bmi", "alt"]):
            suggestions.append("histogram - to show the distribution of numerical variables")
        
        if any(word in query_lower for word in ["smoker", "gender", "copd", "readmitted"]):
            suggestions.append("bar chart - to show counts of categorical variables")
            suggestions.append("pie chart - to show proportions of categories")
        
        if any(word in query_lower for word in ["relationship", "correlation", "vs"]):
            suggestions.append("scatter plot - to show relationships between numerical variables")
        
        if any(word in query_lower for word in ["compare", "comparison", "by"]):
            suggestions.append("box plot - to compare numerical variables across categories")
        
        if suggestions:
            return "Suggested visualizations:\n" + "\n".join(f"• {s}" for s in suggestions)
        else:
            return "Consider using: bar chart, histogram, scatter plot, or box plot based on your data type"