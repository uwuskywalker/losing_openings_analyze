import { useEffect, useState } from 'react';
import type { Game } from '../types/Game.ts';

export function MatchHistory({ username, source }: { username: string, source: string }) {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`/api/fetch-games?username=${username}&source=${source}`);
        if (!response.ok) throw new Error("API 請求失敗");
        const data = await response.json();
        setGames(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error("Failed to fetch games:", error);
        setGames([]); //
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [username, source]);

  if (loading) return <div>載入中...</div>;

  return (
    <table>
      <thead>
        <tr>
          <th>日期</th>
          <th>模式</th>
          <th>等級分</th>
          <th>結果</th>
        </tr>
      </thead>
      <tbody>
        {Array.isArray(games) && games.map((game, index) => (
          <tr key={index} style={{ color: game.result === 'win' ? 'green' : 'red' }}>
            <td>{game.date}</td>
            <td>{game.mode}</td>
            <td>{game.rating}</td>
            <td>{game.result === 'win' ? '勝' : '敗'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}