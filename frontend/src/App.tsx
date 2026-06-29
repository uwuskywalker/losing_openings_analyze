// frontend/src/App.tsx
import { useState } from 'react';
import './App.css';
import FetcherForm from './components/FetcherForm';
import { MatchHistory } from './components/MatchHistory';
import ChessLogo from './assets/Chesscom.webp';
import LichessLogo from './assets/lichess.webp';

export default function App() {
  const [source, setSource] = useState<'chess.com' | 'lichess'>('chess.com');
  const [searchParams, setSearchParams] = useState<{ username: string; source: string } | null>(null);

  const handleFetch = (username: string) => {
    // 觸發搜尋，更新參數
    setSearchParams({ username, source });
  };

  return (
    <div className="app-shell">
      <div className="source-toggle">
        <button
          className={`source-btn ${source === 'chess.com' ? 'active' : ''}`}
          onClick={() => setSource('chess.com')}
        >
          <img src={ChessLogo} alt="Chess.com" className="source-icon" />
          <span>Chess.com</span>
        </button>

        <button
          className={`source-btn ${source === 'lichess' ? 'active' : ''}`}
          onClick={() => setSource('lichess')}
        >
          <img src={LichessLogo} alt="Lichess" className="source-icon" />
          <span>Lichess</span>
        </button>
      </div>

      <FetcherForm onFetch={handleFetch} />

      {/* 只有當搜尋參數存在時，才渲染 MatchHistory */}
      {searchParams && (
        <div className="results-panel">
          <MatchHistory
            username={searchParams.username}
            source={searchParams.source}
          />
        </div>
      )}
    </div>
  );
}