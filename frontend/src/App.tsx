// frontend/src/App.tsx
import { useState } from 'react';
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
      <div style={{ 
        textAlign: 'center', 
        padding: '50px', 
        backgroundColor: '#222', 
        color: '#fff', 
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
    }}>
      
      <div style={{ display: 'flex', gap: '10px' }}>
      <button onClick={() => setSource('chess.com')} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <img src={ChessLogo} alt="Chess.com" style={{ width: '20px', height: '20px' }} />
        Chess.com
      </button>

      <button onClick={() => setSource('lichess')} style={{ marginLeft: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <img src={LichessLogo} alt="Lichess" style={{ width: '20px', height: '20px' }} />
        Lichess
      </button>
      </div>

      <FetcherForm onFetch={handleFetch} />
      
      {/* 只有當搜尋參數存在時，才渲染 MatchHistory */}
      {searchParams && (
        <div style={{ marginTop: '30px', width: '100%', maxWidth: '800px' }}>
          <MatchHistory 
            username={searchParams.username} 
            source={searchParams.source} 
          />
        </div>
      )}
    </div>
  );
}