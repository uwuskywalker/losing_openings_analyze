import { useEffect, useState } from 'react';
import type { Game } from '../types/Game.ts';

// 1. 定義資料結構型別
interface BlindSpot {
  eco: string;
  opening_name: string;
  loss_count: number;
}

interface ApiResponse {
  player_info: { username: string; total_games_analyzed: number; total_losses: number };
  recent_games: Game[];
  top_blind_spots: BlindSpot[];
}

export function MatchHistory({ username, source }: { username: string, source: string }) {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`/api/fetch-games?username=${username}&source=${source}`);
        if (!response.ok) throw new Error("API 請求失敗");
        const json = await response.json();
        setData(json); // 直接存取完整的 API 回應物件
      } catch (error) {
        console.error("Failed to fetch games:", error);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [username, source]);

  if (loading) return <div>載入中...</div>;
  if (!data) return <div>無法載入資料</div>;

  return (
    <div>
      {/* 2. 顯示盲點報告 */}
      <section>
        <h3>開局盲點分析 (近期最常輸)</h3>
        <ul>
          {data?.top_blind_spots?.map((spot, index) => (
            <li key={index}>
              {spot.eco} - {spot.opening_name}: 輸了 {spot.loss_count} 場
            </li>
          ))}
        </ul>
      </section>

      {/* 3. 顯示對局列表 */}
      <section>
        <h3>最近對局</h3>
        <table>
          <thead>
            <tr><th>日期</th><th>模式</th><th>ECO</th><th>結果</th></tr>
          </thead>
          <tbody>
            {data?.recent_games?.map((game, index) => (
              <tr key={index} style={{ color: game.result === 'win' ? 'green' : 'red' }}>
                <td>{game.date}</td>
                <td>{game.mode}</td>
                <td>{game.eco || 'N/A'}</td>
                <td>{game.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}