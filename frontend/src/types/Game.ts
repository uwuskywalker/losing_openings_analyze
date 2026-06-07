export interface Game {
  username: string;
  rating: number;
  date: string;
  result: 'win' | 'loss';
  mode: string;
}