class ResticError(Exception):
    """Restic 基础异常类"""

    pass


class ResticConfigError(ResticError):
    """Restic 配置错误"""

    pass


class ResticRepositoryError(ResticError):
    """Restic 仓库错误"""

    pass


class ResticPasswordError(ResticRepositoryError):
    """Restic 密码错误"""

    pass


class ResticCommandError(ResticError):
    """Restic 命令执行错误"""

    pass
