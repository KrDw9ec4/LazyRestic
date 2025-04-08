#!/bin/bash

# =====================================================
# LazyRestic - restic-backup-template.sh
# Description: Backup data using restic
# Author: ChatGPT
# =====================================================

# ===== 函数定义 =====
# 日志函数（带时间戳）
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 错误通知函数
notify_error() {
    local message="$1"
    if [[ -n "$NTFY_URL" && -n "$NTFY_TOPIC" && -n "$NTFY_TOKEN" ]]; then
        curl -s \
            -H "Authorization: Bearer $NTFY_TOKEN" \
            -H "Title: $SCRIPT_NAME" \
            -H "Tags: $RESTIC_BACKUP_TAG" \
            -d "$message" \
            "$NTFY_URL/$NTFY_TOPIC" >/dev/null
    fi
}

# 加载配置文件
load_env() {
    if [[ -f "$1" ]]; then
        # shellcheck disable=SC1090
        source "$1"
    else
        log "[ERROR] 配置文件未找到: $1"
        notify_error "配置文件未找到: $1"
        exit 1
    fi
}

# 检测 restic 流程
restic_check() {
    # 检查 restic 是否安装
    if ! command -v restic &>/dev/null; then
        log "[ERROR] restic 未安装，请先安装 restic。"
        notify_error "restic 未安装，请先安装 restic。"
        exit 1
    fi

    # 检查环境变量 RESTIC_REPOSITORY 和 RESTIC_PASSWORD_FILE 是否设置
    if [[ -z "${RESTIC_REPOSITORY:-}" || -z "${RESTIC_PASSWORD_FILE:-}" ]]; then
        log "[ERROR] restic 配置不完整：请确保 RESTIC_REPOSITORY 和 RESTIC_PASSWORD_FILE 已设置。"
        notify_error "restic 配置不完整：请确保 RESTIC_REPOSITORY 和 RESTIC_PASSWORD_FILE 已设置。"
        exit 1
    fi

    # 检查仓库是否已初始化
    if restic cat config &>/dev/null; then
        log "[INFO] restic 仓库已初始化。"
    else
        local exit_code=$?
        if [[ $exit_code -eq 10 ]]; then
            log "[ERROR] restic 仓库未初始化，请先运行 'restic init' 初始化。"
            notify_error "restic 仓库未初始化，请先运行 'restic init' 初始化。"
        else
            log "[ERROR] 无法检查 restic 仓库：可能是密码错误或其他问题。"
            notify_error "无法检查 restic 仓库：请检查密码文件或仓库路径。"
        fi
        exit 1
    fi
}

# ===== 变量声明 =====
# 定义脚本根目录
BASE_DIR="$(dirname "$0")/.."
SCRIPT_NAME="$(basename "$0" .sh)"

LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/restic-backup-$(date '+%Y%m').log"

# 检查是否传入配置名称参数
if [[ -z "$1" ]]; then
    log "[ERROR] 未传入配置名称。用法：$(basename "$0") <config-name>"
    exit 1
fi

CONFIG_NAME="$1"
load_env "$BASE_DIR/configs/$CONFIG_NAME"

RESTIC_BACKUP_EXCLUDE="$BASE_DIR/configs/$RESTIC_BACKUP_EXCLUDE_NAME"

# ===== 主流程 =====
# 确保日志目录存在
mkdir -p "$LOG_DIR"
log "[INFO] 开始备份任务：$SCRIPT_NAME"

# 检查 restic 流程
restic_check

# 执行 restic 备份
log "[INFO] 执行 restic backup ..."

restic backup "$RESTIC_BACKUP_SOURCE" \
    --exclude-file="$RESTIC_BACKUP_EXCLUDE" \
    --tag "$RESTIC_BACKUP_TAG" \
    --skip-if-unchanged 2>&1 | tee -a "$LOG_FILE"

BACKUP_STATUS=${PIPESTATUS[0]}

if [[ $BACKUP_STATUS -ne 0 ]]; then
    log "[ERROR] 备份失败，退出码：$BACKUP_STATUS"
    notify_error "备份失败，脚本: $SCRIPT_NAME，退出码: $BACKUP_STATUS"
    exit "$BACKUP_STATUS"
fi

log "[INFO] 备份任务完成：$SCRIPT_NAME"

exit 0
