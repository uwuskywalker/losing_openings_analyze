from platforms.chess_com import ChessComPlatform
from platforms.lichess import LichessPlatform

_PLATFORMS = {
    'chess.com': ChessComPlatform,
    'lichess': LichessPlatform
}

def get_platform(source, username):
    platform_class = _PLATFORMS.get(source.lower())
    if not platform_class:
        raise ValueError(f"不支援的平台: {source}")
    return platform_class(username)