import React, { useState } from 'react';
import { Citation } from '../types/chat.types';
import { truncateText } from '../utils/formatters';

interface CitationCardProps {
  citations: Citation[];
  className?: string;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citations,
  className = '',
}) => {
  const [expandedCitations, setExpandedCitations] = useState<Set<number>>(new Set());

  if (!citations || citations.length === 0) {
    return null;
  }

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedCitations);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedCitations(newExpanded);
  };

  return (
    <div className={`border border-blue-200 bg-blue-50 rounded-lg ${className}`}>
      <div className="p-3">
        {/* Header */}
        <div className="flex items-center space-x-2 mb-3">
          <div className="flex items-center justify-center w-6 h-6 bg-blue-500 rounded-full flex-shrink-0">
            <span className="text-white text-sm font-bold">📚</span>
          </div>
          <h4 className="font-medium text-blue-800">
            Source{citations.length > 1 ? 's' : ''}
            <span className="text-blue-600 font-normal ml-1">
              ({citations.length} document{citations.length > 1 ? 's' : ''})
            </span>
          </h4>
        </div>

        {/* Citations list */}
        <div className="space-y-3">
          {citations.map((citation, index) => {
            const isExpanded = expandedCitations.has(index);
            const excerptLength = citation.excerpt.length;
            const shouldTruncate = excerptLength > 200;
            const displayExcerpt = shouldTruncate && !isExpanded 
              ? truncateText(citation.excerpt, 200)
              : citation.excerpt;

            return (
              <div
                key={index}
                className="bg-white border border-blue-200 rounded-lg p-3 hover:shadow-sm transition-shadow"
              >
                {/* Citation header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h5 className="font-medium text-gray-900 truncate">
                      {citation.title}
                    </h5>
                    <div className="flex items-center space-x-3 mt-1">
                      <p className="text-sm text-gray-600 truncate">
                        {citation.documentId}
                      </p>
                      {citation.page && (
                        <span className="text-sm text-gray-500">
                          Page {citation.page}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Citation number */}
                  <span className="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 bg-blue-100 text-blue-800 text-xs font-medium rounded-full ml-2">
                    {index + 1}
                  </span>
                </div>

                {/* Citation excerpt */}
                <div className="text-sm text-gray-700 leading-relaxed">
                  <p className="whitespace-pre-wrap">{displayExcerpt}</p>
                  
                  {/* Expand/collapse button */}
                  {shouldTruncate && (
                    <button
                      onClick={() => toggleExpanded(index)}
                      className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium focus:outline-none focus:underline"
                    >
                      {isExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>

                {/* Citation metadata */}
                {(excerptLength > 0) && (
                  <div className="mt-2 pt-2 border-t border-gray-100">
                    <p className="text-xs text-gray-500">
                      Excerpt length: {excerptLength} characters
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        {citations.length > 1 && (
          <div className="mt-3 pt-3 border-t border-blue-200">
            <p className="text-xs text-blue-700 text-center">
              Information compiled from {citations.length} medical documents
            </p>
          </div>
        )}
      </div>
    </div>
  );
};