import React from 'react';

type Source = 'chess.com' | 'lichess';

interface Props {
  selectedSource: Source;
  onSelect: (source: Source) => void;
}

export default function SourceSelector({ selectedSource, onSelect }: Props) {
  return (
    <div className="flex gap-4 mb-6">
      {(['chess.com', 'lichess'] as Source[]).map((source) => (
        <button
          key={source}
          onClick={() => onSelect(source)}
          className={`flex-1 p-4 rounded-xl border-2 transition-all ${
            selectedSource === source
              ? 'border-amber-500 bg-neutral-800 text-amber-500'
              : 'border-transparent bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
          }`}
        >
          {source.charAt(0).toUpperCase() + source.slice(1)}
        </button>
      ))}
    </div>
  );
}