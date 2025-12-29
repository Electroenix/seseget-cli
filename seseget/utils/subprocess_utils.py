import subprocess
from .trace import *


def exec_cmd(command, shell=False):
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="ignore"
    )

    try:
        while True:
            line = process.stdout.readline()
            if line:
                SESE_PRINT(line, end="")
            if not line and process.poll() is not None:
                break

        return_code = process.wait()

        if return_code == 0:
            return True
        else:
            SESE_TRACE(LOG_ERROR, f"命令执行失败，返回码[{return_code}]，命令{command}")
            return False

    except subprocess.TimeoutExpired:
        SESE_TRACE(LOG_ERROR, "命令执行超时")
        process.kill()
        return False
    except FileNotFoundError:
        SESE_TRACE(LOG_ERROR, "找不到命令文件")
        return False
    except Exception as e:
        SESE_TRACE(LOG_ERROR, f"执行命令时发生错误: {str(e)}")
        return False
