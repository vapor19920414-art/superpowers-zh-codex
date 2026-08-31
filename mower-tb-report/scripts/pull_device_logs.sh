#!/usr/bin/env bash
# 从割草机实机（10.5.5.1）拉指定日期的 ROS 节点日志到本地。
# 用法: pull_device_logs.sh [YYYY-MM-DD] [本地目录] [节点 ...]
#   pull_device_logs.sh                                  # 拉今天，默认 4 节点
#   pull_device_logs.sh 2026-08-10 ./223 mcu_communication_node shell_node
set -euo pipefail
DEV=root@10.5.5.1
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new)
DATE="${1:-$(date +%F)}"
OUT="${2:-./device_logs_${DATE}}"
NODES=("${@:3}")
[ ${#NODES[@]} -eq 0 ] && NODES=(mcu_communication_node shell_node mission_controller_node system_manager_node)

mkdir -p "$OUT"
echo "[info] 连接 $DEV …"
ssh "${SSH_OPTS[@]}" "$DEV" true 2>/dev/null || { echo "[error] 连不上 $DEV，确认本机已接入 10.5.5.x 子网" >&2; exit 1; }

REMOTE_DATE=$(date -d "$DATE" +%Y%m%d 2>/dev/null || date -j -f %F "$DATE" +%Y%m%d 2>/dev/null || echo "")
# 在设备上 find 当天文件 → 流式 tar 回来
find_cmd="find"
for n in "${NODES[@]}"; do
  find_cmd+=" /userdata/log/$n/daily /userdata/log/$n/boot"
done
find_cmd+=" -type f \\( -name '*_${DATE}*.log' -o -name 'boot_${REMOTE_DATE}*.log' \\) -print0"

ssh "${SSH_OPTS[@]}" "$DEV" "cd /userdata/log && $find_cmd | tar --null -czf - -T -" \
  | tar -xzf - -C "$OUT" 2>/dev/null && echo "[ok] 节点日志 → $OUT"

# 顺手拉最近的 coredump（若有）
mkdir -p "$OUT/coredump"
ssh "${SSH_OPTS[@]}" "$DEV" "ls -t /userdata/log/coredump/core-* 2>/dev/null | head -3" \
  | while read -r f; do
      [ -n "$f" ] && scp -q "${SSH_OPTS[@]}" "$DEV:$f" "$OUT/coredump/" 2>/dev/null && echo "[ok] coredump $f"
    done || true

echo "[done] 共 $(find "$OUT" -type f | wc -l) 个文件 → $OUT"
find "$OUT" -type f | head -30
