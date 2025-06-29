import json
import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

from restic.error import (
    ResticCommandError,
    ResticConfigError,
    ResticError,
    ResticPasswordError,
    ResticRepositoryError,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/restic.log"),  # 保存到文件
        logging.StreamHandler(),  # 输出到终端
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class ResticConfig:
    repository: str
    password: str
    path: str = "restic"


class Restic:
    def __init__(self, config: ResticConfig, auto_init: bool = False):
        self.config = config
        self.auto_init = auto_init

        try:
            # ResticConfig 验证
            self._validate_restic_config()
            # 检查仓库是否已初始化
            self._exec(command="cat", args=["config"])
        except ResticConfigError as e:
            logger.error(f"ResticConfig 无效: {e}")
            raise
        except ResticPasswordError:
            raise
        except ResticRepositoryError:
            if self.auto_init:
                logger.info("仓库未初始化，正在自动初始化...")
                self._exec(command="init")
            else:
                logger.error("仓库可能未初始化，请手动初始化")
                raise

    def _validate_restic_config(self) -> None:
        """
        验证 ResticConfig 的有效性

        Raises:
            ResticConfigError: 如果配置无效或缺少必要参数
        """
        try:
            # 检查二进制文件是否存在
            if not shutil.which(self.config.path):
                raise ResticConfigError(
                    f"Restic 二进制文件 '{self.config.path}' 不存在"
                )
            # 检查仓库路径和密码是否提供
            if not self.config.repository:
                raise ResticConfigError("Restic 仓库路径未提供")
            if not self.config.password:
                raise ResticConfigError("Restic 密码未提供")
        except ResticConfigError:
            # 捕获 ResticConfigError 并重新抛出
            raise
        except Exception as e:
            # 包装非预期错误
            raise ResticConfigError(f"Restic 配置错误: {e}")

        logger.debug("ResticConfig 验证通过")

    def _exec(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        # json_output: bool = True,
        timeout: Optional[int] = None,
    ):
        """
        执行 `restic <command> [args...]` 命令

        Args:
            command: 要执行的 Restic 命令
            args: 附加参数列表
            env: 环境变量字典
            timeout: 命令超时时间（秒）

        Returns:
            str: 命令执行的标准输出

        Raises:
            ResticCommandError: 如果命令执行失败或返回非零状态码
            ResticPasswordError: 如果密码错误
            ResticRepositoryError: 如果存储库相关错误
            ResticError: 其他 Restic 错误
        """
        # 构建执行命令
        cmd = [self.config.path, command]

        if args:
            cmd.extend(args)  # 附加参数

        cmd.append("--json")  # 添加 JSON 输出选项

        logger.debug(f"准备执行命令: {' '.join(cmd)}")

        # 构建运行时环境变量
        _env = self._get_env()

        if env:
            _env.update(env)

        # 执行命令
        try:
            process = subprocess.run(
                cmd,
                env=_env,  # 设置环境变量
                check=False,  # 不抛出异常，手动处理
                capture_output=True,  # 捕获输出
                text=True,  # 以文本模式处理输出
                encoding="utf-8",  # 设置编码
                timeout=timeout,  # 设置超时时间
            )
        except subprocess.TimeoutExpired:
            error_msg = f"执行 {command} 命令超时"
            logger.error(error_msg)
            raise ResticCommandError(error_msg)
        except Exception as e:
            raise ResticCommandError(f"执行 {command} 失败: {e}")

        logger.debug(f"执行 {command} 完成，返回码： {process.returncode}")

        # 检查返回码并处理错误
        if process.returncode != 0:
            self._handle_command_error(command, process.returncode, process.stderr)

        return process.stdout

    def _get_env(self) -> Dict[str, str]:
        """获取环境变量"""
        _env = {
            "RESTIC_REPOSITORY": self.config.repository,
            "RESTIC_PASSWORD": self.config.password,
        }
        # 添加系统环境变量
        system = platform.system()
        if system == "Windows":
            logger.debug("检测到 Windows 环境")
            _env["PATH"] = os.environ.get("PATH", "")
            _env["LOCALAPPDATA"] = os.environ.get("LOCALAPPDATA", "~/AppData/Local")
            _env["TMP"] = os.environ.get("TMP", "~/AppData/Local/Temp")
            _env["TEMP"] = os.environ.get("TEMP", "~/AppData/Local/Temp")
        elif os.environ.get("PREFIX"):  # 判断为 Termux 环境
            logger.debug("检测到 Termux 环境")
            _env["PATH"] = os.environ.get("PATH", "/data/data/com.termux/files/usr/bin")
            _env["TMPDIR"] = os.environ.get(
                "TMPDIR", "/data/data/com.termux/files/usr/tmp"
            )
        elif system in ("Linux", "Darwin"):
            logger.debug("检测到 Linux 或 macOS 环境")
            _env["PATH"] = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
            _env["TMPDIR"] = os.environ.get("TMPDIR", "/tmp")

        return _env

    def _handle_command_error(
        self, command: str, return_code: int, stderr: str
    ) -> None:
        """
        根据返回码处理命令错误

        Args:
            command: 执行的命令
            return_code: 命令返回码
            stderr: 错误输出

        Raises:
            相应的异常类型
        """

        # 参考 https://restic.readthedocs.io/en/latest/075_scripting.html#exit-codes
        error_messages = {
            1: "命令执行失败",
            2: "Go 运行时错误",
            3: "命令执行失败",
            10: "存储库不存在",  # 自 Restic 0.17.0 起
            11: "无法锁定存储库",  # 自 Restic 0.17.0 起
            12: "密码错误",  # 自 Restic 0.17.1 起
            130: "命令被中断",
        }

        base_msg = error_messages.get(return_code, "发生意外错误")
        base_error_msg = f"执行 {command} 失败: {base_msg}"
        full_error_msg = base_error_msg

        if stderr:
            stderr.strip()  # 清理错误输出的前后空白
            try:
                stderr_json: dict = json.loads(stderr)
                logger.debug(f"JSON 解析成功：{stderr_json}")
                full_error_msg += (
                    f", 错误信息: {stderr_json.get('message', '未知错误')}"
                )
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析失败：{e}，返回原始错误信息")
                full_error_msg += f", 错误信息: {stderr}"

        logger.error(full_error_msg)

        # 根据返回码抛出相应的异常
        match return_code:
            case 2:
                raise ResticError(base_error_msg)
            case 10 | 11:
                raise ResticRepositoryError(base_error_msg)
            case 12:
                raise ResticPasswordError(base_error_msg)
            case _:
                raise ResticCommandError(base_error_msg)
