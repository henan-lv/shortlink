#!/usr/bin/env bash
# 备份 MySQL 数据
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="$HOME/shortlink-backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/shortlink_${TIMESTAMP}.sql.gz"

echo "==> 备份 MySQL -> $BACKUP_FILE"

docker exec shortlink_mysql sh -c 'exec mysqldump --single-transaction --routines --triggers -uroot -p"$MYSQL_ROOT_PASSWORD" shortlink' \
    | gzip > "$BACKUP_FILE"

echo "==> 备份完成: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"

# 保留最近 30 天
find "$BACKUP_DIR" -name "shortlink_*.sql.gz" -mtime +30 -delete
echo "==> 已清理 30 天前的旧备份"
