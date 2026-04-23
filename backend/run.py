#!/usr/bin/env python3
"""启动脚本"""
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件，必须在导入 app 之前

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
