"""
開発サーバー起動スクリプト
"""

import os
import uvicorn
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    print(f"Starting server at http://{host}:{port}")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # 開発時はホットリロード有効
    )
