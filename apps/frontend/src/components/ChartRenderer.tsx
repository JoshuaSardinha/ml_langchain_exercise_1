import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { ChartData } from '../types/chat.types';

interface ChartRendererProps {
  chartData: ChartData;
  className?: string;
}

// Default colors for charts
const CHART_COLORS = [
  '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
  '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
];

export const ChartRenderer: React.FC<ChartRendererProps> = ({
  chartData,
  className = '',
}) => {
  const { type, data, options = {} } = chartData;

  // Default chart configuration
  const defaultConfig = {
    width: 600,
    height: 300,
    margin: { top: 20, right: 30, left: 20, bottom: 20 },
    ...options,
  };

  // Custom tooltip formatter
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          {label && <p className="font-medium text-gray-900">{`${label}`}</p>}
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              <span className="font-medium">{entry.dataKey}:</span>{' '}
              <span>{typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    if (!data || (Array.isArray(data) && data.length === 0)) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
          <div className="text-center text-gray-500">
            <div className="text-4xl mb-2">📊</div>
            <p>No data to display</p>
          </div>
        </div>
      );
    }

    switch (type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={defaultConfig.height}>
            <BarChart data={data} margin={defaultConfig.margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {Object.keys(data[0] || {})
                .filter(key => key !== 'name')
                .map((key, index) => (
                  <Bar 
                    key={key} 
                    dataKey={key} 
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                    radius={[2, 2, 0, 0]}
                  />
                ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={defaultConfig.height}>
            <LineChart data={data} margin={defaultConfig.margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {Object.keys(data[0] || {})
                .filter(key => key !== 'name')
                .map((key, index) => (
                  <Line 
                    key={key} 
                    type="monotone" 
                    dataKey={key} 
                    stroke={CHART_COLORS[index % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS[index % CHART_COLORS.length], r: 4 }}
                  />
                ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={defaultConfig.height}>
            <PieChart margin={defaultConfig.margin}>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={Math.min(defaultConfig.height, 250) / 3}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={defaultConfig.height}>
            <ScatterChart data={data} margin={defaultConfig.margin}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis 
                type="number" 
                dataKey="x" 
                name="X" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <YAxis 
                type="number" 
                dataKey="y" 
                name="Y" 
                tick={{ fontSize: 12 }}
                stroke="#6B7280"
              />
              <Tooltip 
                cursor={{ strokeDasharray: '3 3' }}
                content={<CustomTooltip />}
              />
              <Legend />
              <Scatter name="Data Points" data={data} fill={CHART_COLORS[0]} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-2">❓</div>
              <p>Unsupported chart type: {type}</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      {/* Chart title */}
      {options.title && (
        <h3 className="text-lg font-medium text-gray-900 mb-4 text-center">
          {options.title}
        </h3>
      )}

      {/* Chart container */}
      <div className="overflow-x-auto">
        {renderChart()}
      </div>

      {/* Chart description */}
      {options.description && (
        <p className="text-sm text-gray-600 mt-2 text-center">
          {options.description}
        </p>
      )}

      {/* Chart metadata */}
      {Array.isArray(data) && data.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-500 text-center">
            Showing {data.length} data {data.length === 1 ? 'point' : 'points'}
          </p>
        </div>
      )}
    </div>
  );
};