// frontend/src/components/FetcherForm.tsx
import { useState } from 'react';

export default function FetcherForm({ onFetch }: { onFetch: (username: string) => void }) {
  const [username, setUsername] = useState('');

  return (
    <div style={{ marginTop: '20px' }}>
      <input
        type="text"
        placeholder="請輸入棋手名稱..."
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        style={{ padding: '8px', width: '200px' }}
      />
      <button 
        onClick={() => onFetch(username)}
        style={{ padding: '8px 15px', marginLeft: '10px', cursor: 'pointer' }}
      >
        搜尋對局
      </button>
    </div>
  );
}