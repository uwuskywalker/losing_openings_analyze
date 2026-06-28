import { useEffect, useState } from 'react';
import type { Game } from '../types/Game.ts';

// 1. 定義後端全新回傳資料的 TypeScript 介面
interface BlindSpot {
  eco: string;
  opening_name: string;
  loss_count: number;
}

interface PlayerInfo {
  username: string;
  total_games_analyzed: number;
  total_losses: number;
}

interface ApiResponse {
  player_info: PlayerInfo;
  recent_games: Game[];
  top_blind_spots: BlindSpot[];
}

export function MatchHistory({ username, source }: { username: string, source: string }) {
  // 修改狀態：改為儲存整個物件，預設為 null
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`/api/fetch-games?username=${username}&source=${source}`);
        if (!response.ok) throw new Error("API 請求失敗");
        const resData: ApiResponse = await response.json();
        
        // 直接存入整包物件
        setData(resData); 
      } catch (error) {
        console.error("Failed to fetch games:", error);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [username, source]);

  if (loading) return <div style={{ padding: '20px' }}>數據分析中，請稍候...</div>;
  if (!data) return <div style={{ padding: '20px', color: 'red' }}>無法載入分析資料</div>;

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      
      {/* 區塊一：玩家基本戰報 */}
      <div style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 10px 0' }}>📊 玩家棋局概況</h3>
        <p style={{ margin: '5px 0' }}>帳號：<strong>{data.player_info.username}</strong></p>
        <p style={{ margin: '5px 0' }}>分析總局數：{data.player_info.total_games_analyzed} 場</p>
        <p style={{ margin: '5px 0' }}>近期敗局：<span style={{ color: '#d9534f', fontWeight: 'bold' }}>{data.player_info.total_losses}</span> 場</p>
      </div>

      {/* 區塊二：開局盲點報告 (從 PostgreSQL 查出來的寶貴資料！) */}
      <div style={{ background: '#fff5f5', padding: '15px', borderRadius: '8px', borderLeft: '5px solid #d9534f', marginBottom: '20px' }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#c9302c' }}>⚠️ 近期開局盲點 (最常輸的 ECO 前 5 名)</h3>
        {data.top_blind_spots.length === 0 ? (
          <p>近期沒有顯著的敗局開局紀錄。</p>
        ) : (
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {data.top_blind_spots.map((spot, idx) => (
              <li key={idx} style={{ margin: '8px 0' }}>
                <strong style={{ color: '#333' }}>{spot.eco}</strong> - <span style={{ fontWeight: 500 }}>{spot.opening_name}</span> 
                ：近期輸了 <span style={{ color: '#d9534f', fontWeight: 'bold' }}>{spot.loss_count}</span> 次
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 區塊三：最近對局紀錄 */}
      <div>
        <h3 style={{ margin: '0 0 10px 0' }}>📜 最近對局歷史</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#f1f1f1', borderBottom: '2px solid #ccc' }}>
              <th style={{ padding: '10px' }}>日期</th>
              <th style={{ padding: '10px' }}>模式</th>
              <th style={{ padding: '10px' }}>ECO</th>
              <th style={{ padding: '10px' }}>等級分</th>
              <th style={{ padding: '10px' }}>結果</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_games.map((game, index) => {
              // 判定和局(draw)或勝負，給予不同顏色
              let resultColor = '#777'; // 和局灰色
              let resultText = '和';
              if (game.result === 'win') { resultColor = '#2b8a3e'; resultText = '勝'; }
              if (game.result === 'loss') { resultColor = '#c92a2a'; resultText = '敗'; }

              return (
                <tr key={index} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px' }}>{game.date}</td>
                  <td style={{ padding: '10px' }}>{game.mode || 'N/A'}</td>
                  <td style={{ padding: '10px' }}><strong>{game.eco || 'N/A'}</strong></td>
                  <td style={{ padding: '10px' }}>{game.rating || 'N/A'}</td>
                  <td style={{ padding: '10px', color: resultColor, fontWeight: 'bold' }}>{resultText}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
}