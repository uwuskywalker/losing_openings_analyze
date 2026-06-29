// frontend/src/components/FetcherForm.tsx
import { useState } from 'react';

export default function FetcherForm({ onFetch }: { onFetch: (username: string) => void }) {
  const [username, setUsername] = useState('');

  return (
    <div className="search-panel">
      <input
        className="search-input"
        type="text"
        placeholder="請輸入棋手名稱..."
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            onFetch(username);
          }
        }}
      />
      <button
        className="search-button"
        onClick={() => onFetch(username)}
      >
        搜尋對局
      </button>
    </div>
  );
}