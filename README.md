# LazyRestic

一个基于 [restic](https://restic.net/) 的自动化备份脚本，支持 Ntfy 通知，方便在备份失败时立即推送通知。

## 项目结构

```
LazyRestic
├── client
│   └── restic-backup-ntfy.sh # 备份主脚本
├── configs
│   ├── config-template-ntfy.env # 配置文件模板
│   ├── passwd-hostname.key # Restic 仓库密码文件
│   └── exclude-default.txt # 默认排除表
├── logs
│   ├── .gitkeep
│   └── restic-backup-202504.log # 备份日志
├── server
└── README.md
```

## 使用方法

克隆并进入本仓库：

```bash
cd ~
git clone https://github.com/KrDw9ec4/LazyRestic.git
cd LazyRestic
```

添加并[修改配置文件](#配置说明)：

```bash
cp configs/config-template-ntfy.env configs/config-compose-ntfy.env
vim configs/config-compose-ntfy.env
```

```diff
# ===== Restic 仓库配置 =====

export RESTIC_HOST="$HOSTNAME"
-export RESTIC_REPOSITORY=/path/to/restic/repo
+export RESTIC_REPOSITORY=rest:http://10.1.1.102:8888/appdata
-export RESTIC_PASSWORD_FILE=/path/to/restic/passwdfile
+export RESTIC_PASSWORD_FILE=/home/krdw/LazyRestic/configs/passwd-prod.key

# ===== 可修改配置项 =====

# 备份数据源路径
-RESTIC_BACKUP_SOURCE="/path/to/restic/backup/source"
+RESTIC_BACKUP_SOURCE="/home/krdw/compose"

# 备份标签
-RESTIC_BACKUP_TAG="$RESTIC_HOST,template,gold"
+RESTIC_BACKUP_TAG="$RESTIC_HOST,compose,bronze"

# 备份排除文件名称
RESTIC_BACKUP_EXCLUDE_NAME="exclude-default.txt"

# ===== Ntfy 配置 =====

-NTFY_URL=https://ntfy.sh
+NTFY_URL=https://ntfy.example.com
NTFY_TOPIC=restic
-NTFY_TOKEN=tk_xxxxxxx
+NTFY_TOKEN=tk_123456
```

添加密码文件：

```bash
vim /home/krdw/LazyRestic/configs/passwd-prod.key
```


> 若要生成密码：
>
> ```bash
> openssl rand -base64 32 > /home/krdw/LazyRestic/configs/passwd-prod.key
> ```
>
> 然后通过已有的密钥，将新生成的密码添加到仓库中：
>
> ```bash
> source configs/config-compose-ntfy.env
> unset RESTIC_PASSWORD_FILE
> export RESTIC_PASSWORD="xxxxx"
> cat /home/krdw/LazyRestic/configs/passwd-prod.key | restic key add
> ```
>
> ```bash
> unset RESTIC_PASSWORD
> source configs/config-compose-ntfy.env
> restic key list
> ```

确保可访问 restic 仓库并且仓库已初始化：

```bash
source configs/config-compose-ntfy.env
restic cat config
```

执行主脚本：

```bash
/home/krdw/LazyRestic/client/restic-backup-ntfy.sh config-compose-ntfy.env
```

**注意：**

- 需要传入配置文件名，不要含前缀路径（如 `config-compose-ntfy.env`）。

## 脚本功能总结

1. **加载配置文件**
   - 自动加载 `configs/` 目录下的指定 `.env` 配置文件。
   - 如果配置文件缺失，会输出日志并使用 Ntfy 发送错误通知。
2. **Restic 环境检查**
   - 检查 restic 是否安装，仓库是否已初始化，环境变量是否配置完整。
   - 如果检测失败，会输出日志并使用 Ntfy 通知。
3. **执行备份操作**
   - 使用 restic 执行备份，自动使用配置的标签和排除文件。
   - 使用 `--skip-if-unchanged`，如果没有更新数据，则不执行备份。
   - 备份日志会写入 `logs/` 目录下的日志文件。
4. **异常处理**
   - 如果备份失败，自动上报错误信息到 Ntfy 服务器，便于管理者立即知晓。

## 配置说明

所有可配置项放在 `configs/` 目录下，以 `config-` 为前缀的 `.env` 文件。

- **Restic 仓库配置**
  - `RESTIC_HOST` ：本次备份快照的 Host 属性，默认为主机名称 (HOSTNAME)。
  - `RESTIC_REPOSITORY` ：Restic 的仓库地址。
  - `RESTIC_PASSWORD_FILE` ：指向 Restic 仓库密码文件的路径。
- **可修改配置项**
  - `RESTIC_BACKUP_SOURCE` ：需要备份的目录或文件路径。
  - `RESTIC_BACKUP_TAG` ：本次备份快照标签，为多个标签用 `,` 分隔。
  - `RESTIC_BACKUP_EXCLUDE_NAME` ：排除文件名称，无前缀路径。
- **Ntfy 配置**
  - `NTFY_URL` ：Ntfy 服务器地址。
  - `NTFY_TOPIC` ：通知主题。
  - `NTFY_TOKEN` ：推送通知使用的 Token。

---

如有任何问题，欢迎提送 Issue！

Enjoy LazyRestic 🚀

