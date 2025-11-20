# -*- coding: utf-8 -*-
"""
Ollama扫描模块
用于检测Ollama服务的未授权访问漏洞
"""

import socket
import requests
from typing import Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class ScanResult:
    """扫描结果类"""
    
    def __init__(self, host: str, port: int, vulnerable: bool, 
                 version: str = "", models: list = None, error: str = ""):
        self.host = host
        self.port = port
        self.vulnerable = vulnerable
        self.version = version
        self.models = models or []
        self.error = error
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "vulnerable": self.vulnerable,
            "version": self.version,
            "models": ", ".join(self.models) if self.models else "",
            "error": self.error,
            "timestamp": self.timestamp
        }


class OllamaScanner:
    """Ollama扫描器"""
    
    def __init__(self, timeout: int = 5):
        """
        初始化扫描器
        
        Args:
            timeout: 连接超时时间（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scan_single(self, host: str, port: int) -> ScanResult:
        """
        扫描单个目标
        
        Args:
            host: 主机地址
            port: 端口号
            
        Returns:
            ScanResult: 扫描结果
        """
        # 先检查端口是否开放
        if not self._check_port(host, port):
            return ScanResult(host, port, False, error="端口未开放")
        
        # 检查是否为Ollama服务
        try:
            url = f"http://{host}:{port}"
            
            # 获取版本信息
            version_url = f"{url}/api/version"
            response = self.session.get(version_url, timeout=self.timeout)
            
            if response.status_code != 200:
                return ScanResult(host, port, False, error="非Ollama服务")
            
            version_data = response.json()
            version = version_data.get("version", "Unknown")
            
            # 尝试获取模型列表（验证未授权访问）
            tags_url = f"{url}/api/tags"
            tags_response = self.session.get(tags_url, timeout=self.timeout)
            
            if tags_response.status_code == 200:
                tags_data = tags_response.json()
                models = []
                if "models" in tags_data:
                    models = [model.get("name", "") for model in tags_data["models"]]
                
                return ScanResult(host, port, True, version=version, models=models)
            else:
                return ScanResult(host, port, False, version=version, 
                                error=f"无法访问API (状态码: {tags_response.status_code})")
        
        except requests.exceptions.Timeout:
            return ScanResult(host, port, False, error="连接超时")
        except requests.exceptions.ConnectionError:
            return ScanResult(host, port, False, error="连接失败")
        except Exception as e:
            return ScanResult(host, port, False, error=f"扫描错误: {str(e)}")
    
    def _check_port(self, host: str, port: int) -> bool:
        """
        检查端口是否开放
        
        Args:
            host: 主机地址
            port: 端口号
            
        Returns:
            bool: 端口是否开放
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def scan_batch(self, targets: list, threads: int = 10, 
                   callback: Optional[Callable] = None,
                   stop_flag: Optional[Callable] = None) -> list:
        """
        批量扫描目标
        
        Args:
            targets: 目标列表 [(host, port), ...]
            threads: 并发线程数
            callback: 回调函数，每完成一个目标时调用 callback(result, current, total)
            stop_flag: 停止标志函数，返回True时停止扫描
            
        Returns:
            list: 扫描结果列表
        """
        results = []
        total = len(targets)
        current = 0
        
        with ThreadPoolExecutor(max_workers=threads) as executor:
            # 提交所有任务
            future_to_target = {
                executor.submit(self.scan_single, host, port): (host, port)
                for host, port in targets
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_target):
                # 检查停止标志
                if stop_flag and stop_flag():
                    # 取消所有未完成的任务
                    for f in future_to_target:
                        f.cancel()
                    break
                
                try:
                    result = future.result()
                    results.append(result)
                    current += 1
                    
                    # 调用回调函数
                    if callback:
                        callback(result, current, total)
                
                except Exception as e:
                    host, port = future_to_target[future]
                    result = ScanResult(host, port, False, error=f"扫描异常: {str(e)}")
                    results.append(result)
                    current += 1
                    
                    if callback:
                        callback(result, current, total)
        
        return results
    
    def execute_command(self, host: str, port: int, command: str, 
                       model_name: str = None) -> Dict:
        """
        在目标Ollama服务上执行命令
        
        Args:
            host: 主机地址
            port: 端口号
            command: 命令 (list, pull, show, chat, ps, rm, version, help)
            model_name: 模型名称（某些命令需要）
            
        Returns:
            Dict: 执行结果
        """
        url = f"http://{host}:{port}"
        
        try:
            if command == "list":
                response = self.session.get(f"{url}/api/tags", timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data.get("models", [])}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "version":
                response = self.session.get(f"{url}/api/version", timeout=self.timeout)
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "ps":
                response = self.session.get(f"{url}/api/ps", timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data.get("models", [])}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "show" and model_name:
                payload = {"name": model_name}
                response = self.session.post(f"{url}/api/show", 
                                           json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "pull" and model_name:
                payload = {"name": model_name}
                response = self.session.post(f"{url}/api/pull", 
                                           json=payload, timeout=30)
                if response.status_code == 200:
                    return {"success": True, "data": "模型拉取请求已发送"}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "rm" and model_name:
                payload = {"name": model_name}
                response = self.session.delete(f"{url}/api/delete", 
                                             json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    return {"success": True, "data": "模型已删除"}
                else:
                    return {"success": False, "error": f"状态码: {response.status_code}"}
            
            elif command == "chat" and model_name:
                return {"success": False, "error": "chat命令需要在GUI中交互使用"}
            
            else:
                return {"success": False, "error": "无效的命令或缺少参数"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
