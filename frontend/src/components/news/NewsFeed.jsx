import { ExternalLink } from 'lucide-react';

export default function NewsFeed({ articles }) {
  if (!articles || articles.length === 0) {
    return <div className="text-gray-500 text-sm">No news articles available</div>;
  }

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Latest News</h3>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {articles.map((a, i) => (
          <a
            key={i}
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-2 rounded hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-start gap-2">
              <ExternalLink className="w-3 h-3 text-gray-500 mt-1 flex-shrink-0" />
              <div>
                <div className="text-sm text-gray-200 line-clamp-2">{a.title}</div>
                <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-1.5">
                  {a.source === 'reliefweb' && (
                    <span className="text-[10px] px-1 py-0.5 rounded bg-brand-teal/20 text-brand-teal font-medium">RW</span>
                  )}
                  {a.domain} {a.published_at ? `| ${a.published_at.slice(0, 10)}` : ''}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
