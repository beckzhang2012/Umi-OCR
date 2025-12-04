# ==============================================
# =============== Windows系统API ===============
# ==============================================

import os
import subprocess
import winshell  # Windows快捷方式操作
from pathlib import Path

from umi_log import logger
from umi_about import UmiAbout
from .key_translator import getKeyName

# 环境的类型：
# "APPDATA" 用户，低权限要求
# "ProgramData" 全局，高权限要求
EnvType = "APPDATA"  # or "ProgramData"


# ==================== 快捷方式 ====================
class _Shortcut:
    @staticmethod  # 获取地址
    def _getPath(position):
        # 桌面
        if position == "desktop":
            return winshell.desktop()

        startMenu = os.path.join(
            os.getenv(EnvType), "Microsoft", "Windows", "Start Menu"
        )
        # 开始菜单
        if position == "startMenu":
            return startMenu
        # 开机自启
        elif position == "startup":
            return winshell.startup()

    # 创建快捷方式，返回成功与否的字符串。position取值：
    # desktop 桌面
    # startMenu 开始菜单
    # startup 开机自启
    @staticmethod
    def createShortcut(position):
        lnkName = UmiAbout["name"]
        appPath = UmiAbout["app"]["path"]
        if not appPath or not os.path.exists(appPath):
            return f"[Error] 未找到程序exe文件。请尝试手动创建快捷方式。\n[Error] Exe path not exist. Please try creating a shortcut manually.\n\n{appPath}"
        lnkPathBase = _Shortcut._getPath(position)
        lnkPathBase = os.path.join(lnkPathBase, lnkName)
        lnkPath = lnkPathBase + ".lnk"
        i = 1
        while os.path.exists(lnkPath):  # 快捷方式已存在
            lnkPath = lnkPathBase + f" ({i}).lnk"  # 添加序号
            i += 1
        try:
            with winshell.shortcut(lnkPath) as shortcut:
                shortcut.path = appPath
                shortcut.working_directory = os.path.dirname(appPath)
                shortcut.description = UmiAbout["name"]
            return "[Success]"
        except Exception as e:
            return f"[Error] {str(e)}\n请尝试以管理员权限启动软件。\nPlease try starting the software as an administrator.\nappPath: {appPath}\nlnkPath: {lnkPath}"

    # 删除快捷方式，返回删除文件的个数
    @staticmethod
    def deleteShortcut(position):
        lnkName = UmiAbout["name"]
        lnkDir = _Shortcut._getPath(position)
        num = 0
        for fileName in os.listdir(lnkDir):
            if fileName.endswith(".lnk"):
                lnkPath = os.path.join(lnkDir, fileName)
                try:
                    # 检查快捷方式是否指向当前应用
                    with winshell.shortcut(lnkPath) as shortcut:
                        if lnkName in os.path.basename(shortcut.path):
                            os.remove(lnkPath)
                            num += 1
                except Exception:
                    logger.error(
                        f"删除快捷方式失败。 lnkPath: {lnkPath}",
                        exc_info=True,
                        stack_info=True,
                    )
                    continue
        return num


# ==================== 硬件控制 ====================
class _HardwareCtrl:
    # 关机
    @staticmethod
    def shutdown():
        os.system("shutdown /s /t 0")

    # 休眠
    @staticmethod
    def hibernate():
        os.system("shutdown /h")


# ==================== 对外接口 ====================
class Api:
    # 快捷方式。接口： createShortcut deleteShortcut
    # 参数：快捷方式位置， desktop startMenu startup
    Shortcut = _Shortcut()

    # 硬件控制。接口： shutdown hibernate
    HardwareCtrl = _HardwareCtrl()

    # 根据系统及硬件，判断最适合的渲染器类型
    @staticmethod
    def getOpenGLUse():
        import platform

        # 判断系统版本，若 >win10 则使用 GLES ，否则使用软渲染
        version = platform.version()
        if "." in version:
            ver = version.split(".")[0]
            if ver.isdigit() and int(ver) >= 10:
                return "AA_UseOpenGLES"
        return "AA_UseSoftwareOpenGL"

    # 键值转键名
    @staticmethod
    def getKeyName(key):
        return getKeyName(key)

    # 让系统运行一个程序，不堵塞当前进程
    @staticmethod
    def runNewProcess(path, args=""):
        subprocess.Popen(
            f'start "" "{path}" {args}',
            shell=True,
            # 确保在一个新的控制台窗口中运行，与当前进程完全独立。
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    # 用系统默认应用打开一个文件或目录，不堵塞当前进程
    @staticmethod
    def startfile(path):
        os.startfile(path)
