FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY alphazero ./alphazero
COPY api ./api
COPY xq ./xq
COPY web ./web
COPY scripts ./scripts

# 创建必要的目录
RUN mkdir -p /app/data /app/models

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

# 启动命令
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]

