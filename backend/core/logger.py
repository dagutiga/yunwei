import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# 创建日志目录
log_dir = os.path.dirname(os.getenv('LOG_FILE', './logs/vm_management.log'))
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logger.add(
    os.getenv('LOG_FILE', './logs/vm_management.log'),
    level=os.getenv('LOG_LEVEL', 'INFO'),
    rotation="500 MB",
    retention="7 days",
    compression="zip",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | {message}"
)

# 关键：确保导出log变量
log = logger
