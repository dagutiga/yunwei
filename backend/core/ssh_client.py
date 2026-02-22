import paramiko
import os
from dotenv import load_dotenv
from .logger import log

load_dotenv()
SSH_TIMEOUT = int(os.getenv('SSH_TIMEOUT', 10))

class SSHClient:
    def __init__(self, ip: str, port: int, username: str, password: str):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.client = None

    def connect(self):
        """建立SSH连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.ip,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=SSH_TIMEOUT
            )
            log.info(f"SSH连接成功: {self.ip}:{self.port}")
            return True
        except paramiko.AuthenticationException:
            log.error(f"SSH认证失败: {self.ip}:{self.port}")
            return False
        except Exception as e:
            log.error(f"SSH连接失败 {self.ip}:{self.port}: {e}")
            return False

    def execute_command(self, cmd: str) -> tuple:
        """执行SSH命令"""
        if not self.client or not self.client.get_transport().is_active():
            if not self.connect():
                return "", "SSH连接未建立"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            stdout_data = stdout.read().decode('utf-8', errors='ignore')
            stderr_data = stderr.read().decode('utf-8', errors='ignore')
            log.info(f"执行命令 {cmd} on {self.ip}: 输出长度 {len(stdout_data)}, 错误长度 {len(stderr_data)}")
            return stdout_data, stderr_data
        except Exception as e:
            log.error(f"执行命令失败: {e}")
            return "", str(e)

    def close(self):
        """关闭SSH连接"""
        if self.client:
            self.client.close()
            log.info(f"SSH连接已关闭: {self.ip}:{self.port}")
