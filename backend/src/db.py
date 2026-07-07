import os
import psycopg2


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url, sslmode='require')

    db_port = os.getenv('DB_PORT', '5432')
    if db_port and db_port.startswith('='):
        db_port = db_port[1:]

    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=int(db_port) if str(db_port).isdigit() else 5432,
    )


def ensure_game_analysis_table(conn):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_analysis (
                id SERIAL PRIMARY KEY,
                source TEXT NOT NULL,
                username TEXT NOT NULL,
                game_id TEXT NOT NULL,
                played_at DATE,
                rating INTEGER,
                result TEXT,
                mode TEXT,
                eco TEXT,
                opening_name TEXT,
                moves TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (source, username, game_id)
            );
            """
        )
        conn.commit()
    finally:
        cursor.close()


def save_game_analysis(conn, games):
    if not games:
        return

    insert_rows = []
    for game in games:
        game_id = game.get('game_id')
        if not game_id:
            continue

        insert_rows.append(
            (
                game.get('source'),
                game.get('username'),
                game_id,
                game.get('played_at'),
                game.get('rating'),
                game.get('result'),
                game.get('mode'),
                game.get('eco'),
                game.get('opening_name'),
                game.get('moves'),
            )
        )

    if not insert_rows:
        return

    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT INTO game_analysis (
                source, username, game_id, played_at, rating, result, mode, eco, opening_name, moves
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, username, game_id)
            DO UPDATE SET
                played_at = EXCLUDED.played_at,
                rating = EXCLUDED.rating,
                result = EXCLUDED.result,
                mode = EXCLUDED.mode,
                eco = EXCLUDED.eco,
                opening_name = EXCLUDED.opening_name,
                moves = EXCLUDED.moves,
                updated_at = now();
            """,
            insert_rows,
        )
        conn.commit()
    finally:
        cursor.close()


def fetch_stored_games(conn, source, username, limit=100):
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT game_id, played_at, rating, result, mode, eco, opening_name, moves
            FROM game_analysis
            WHERE source = %s AND username = %s
            ORDER BY played_at DESC NULLS LAST, id DESC
            LIMIT %s;
            """,
            (source, username, limit),
        )
        rows = cursor.fetchall()
        results = []
        for row in rows:
            eco_val = row[5]
            opening_name = row[6]
            if opening_name and opening_name != '未知開局':
                eco_out = opening_name
            else:
                eco_out = eco_val

            results.append({
                'source': source,
                'username': username,
                'game_id': row[0],
                'played_at': row[1].isoformat() if row[1] else None,
                'date': row[1].isoformat() if row[1] else 'N/A',
                'rating': row[2],
                'result': row[3],
                'mode': row[4],
                'eco': eco_out,
                'opening_name': opening_name,
                'moves': row[7],
            })

        return results
    finally:
        cursor.close()
