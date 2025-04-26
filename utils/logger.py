import os
import time

class Logger:
    def __init__(self, config):  
        # 创建日志目录
        log_dir = config.get('logging', {}).get('log_dir', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志文件名，使用时间戳
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.log_file = os.path.join(log_dir, f"training_{timestamp}.log")
        
        # 记录初始信息
        with open(self.log_file, 'w') as f:
            f.write(f"训练开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"配置信息: {config}\n\n")
            f.write("训练日志:\n")
    
    def log(self, epoch, metrics):
        message = f"Epoch {epoch+1} | "
    
        for key, value in metrics.items():
            if isinstance(value, (int,float)):
                message += f"{key}: {value:.4f} | "
        print(message)
        # 记录到文件
        with open(self.log_file, 'a') as f:
            f.write(message + '\n')

    def info(self, message):
        # 直接写入日志文件
        with open(self.log_file, 'a') as f:
            f.write(f"[INFO] {message}\n")
    
    def warning(self, message):
        # 直接写入日志文件
        with open(self.log_file, 'a') as f:
            f.write(f"[WARNING] {message}\n")
    
    def error(self, message):
        # 直接写入日志文件
        with open(self.log_file, 'a') as f:
            f.write(f"[ERROR] {message}\n")
    
    def critical(self, message):
        # 直接写入日志文件
        with open(self.log_file, 'a') as f:
            f.write(f"[CRITICAL] {message}\n")
