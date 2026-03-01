import ReactMarkdown from 'react-markdown';
import { Brain } from 'lucide-react';

export default function AIBriefing({ brief }) {
  if (!brief || !brief.content) {
    return (
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
          <Brain className="w-4 h-4 text-brand-teal" />
          AI Situational Brief
        </h3>
        <div className="text-gray-500 text-sm">
          No synthesis available yet. Data ingestion may still be running.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <Brain className="w-4 h-4 text-brand-teal" />
          AI Situational Brief
        </h3>
        {brief.generated_at && (
          <span className="text-xs text-gray-500">
            Generated: {new Date(brief.generated_at).toLocaleString()}
          </span>
        )}
      </div>
      <div className="prose prose-sm prose-invert max-w-none text-gray-300
        prose-headings:text-brand-teal prose-headings:text-sm prose-headings:font-semibold
        prose-p:text-sm prose-li:text-sm prose-strong:text-white">
        <ReactMarkdown>{brief.content}</ReactMarkdown>
      </div>
      {brief.model && (
        <div className="mt-3 text-xs text-gray-600">
          Model: {brief.model} | Local inference
        </div>
      )}
    </div>
  );
}
