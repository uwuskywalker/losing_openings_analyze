// frontend/src/App.tsx
import { useState } from 'react';
import FetcherForm from './components/FetcherForm';
import ChessLogo from './assets/Chesscom.webp';
import LichessLogo from './assets/lichess.webp';

export default function App() {
  const [source, setSource] = useState<'chess.com' | 'lichess'>('chess.com');

  const handleFetch = (username: string) => {
    alert(`正在從 ${source} 抓取 ${username} 的資料...`);
    // 後續這裡會串接你的 API
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
    </div>
  );
}