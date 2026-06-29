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
    <div className="match-history">
      {/* 2. 顯示盲點報告 */}
      <section className="card blindspot-card">
        <h3>常輸開局分析</h3>
        <ul className="blindspots">
          {data?.top_blind_spots?.map((spot, index) => (
            <li key={index} className="blindspot-item">
              <span className="eco">{spot.eco}</span>
              <span className="sep"> - </span>
              <span className="opening">{spot.opening_name}</span>
              <span className="loss">: 輸了 {spot.loss_count} 場</span>
            </li>
          ))}
        </ul>
      </section>

      {/* 3. 顯示對局列表 */}
      <section className="card games-card">
        <h3>最近對局</h3>
        <table className="games-table">
          <thead>
            <tr><th>日期</th><th>模式</th><th>ECO / 開局</th><th>結果</th></tr>
          </thead>
          <tbody>
            {data?.recent_games?.map((game, index) => (
              <tr key={index} className={game.result === 'win' ? 'result-win' : (game.result === 'loss' ? 'result-loss' : 'result-draw')}>
                <td className="col-date">{game.date}</td>
                <td className="col-mode">{game.mode}</td>
                <td className="col-eco" title={`${game.eco || 'N/A'} - ${game.opening_name || '未知開局'}`}>
                  {`${game.eco || 'N/A'} - ${game.opening_name || '未知開局'}`}
                </td>
                <td className="col-result">{game.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}