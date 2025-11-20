# -*- coding: utf-8 -*-
"""
数据解析模块
支持CSV和JSON格式的文件解析
"""

import csv
import json
import re
from typing import List, Tuple, Optional



class DataParser:
    """数据解析器，支持多种格式"""
    
    @staticmethod
    def parse_file(file_path: str) -> List[Tuple[str, int]]:
        """
        解析文件，提取目标列表
        支持格式：CSV, JSON
        """
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.csv'):
            return DataParser._parse_csv(file_path)
        elif file_path_lower.endswith('.json'):
            return DataParser._parse_json(file_path)
        else:
            raise ValueError(f"不支持的文件格式，仅支持 CSV 和 JSON 格式")
    
    @staticmethod
    def _parse_csv(file_path: str) -> List[Tuple[str, int]]:
        """解析CSV文件 - 按列解析"""
        targets = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='gbk') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        
        if not rows:
            return targets
        
        # 查找IP/域名列
        ip_column = None
        port_column = None
        
        # 可能的列名
        ip_names = ['ip', 'IP', 'host', 'Host', 'domain', '域名', 'address', '地址', 'target', '目标']
        port_names = ['port', 'Port', 'PORT', '端口']
        
        headers = rows[0].keys()
        
        for header in headers:
            if any(name in header for name in ip_names):
                ip_column = header
            if any(name in header for name in port_names):
                port_column = header
        
        # 解析数据
        for row in rows:
            if ip_column and ip_column in row:
                host = row[ip_column].strip()
                # 移除http://或https://前缀
                host = host.replace('http://', '').replace('https://', '')
                # 移除路径部分
                if '/' in host:
                    host = host.split('/')[0]
                
                # 获取端口
                port = 11434  # 默认端口
                if port_column and port_column in row and row[port_column]:
                    try:
                        port = int(row[port_column])
                    except:
                        port = 11434
                
                # 如果host中包含端口
                if ':' in host:
                    parts = host.split(':')
                    host = parts[0]
                    try:
                        port = int(parts[1])
                    except:
                        pass
                
                if host:
                    targets.append((host, port))
        
        return targets
    
    @staticmethod
    def _parse_json(file_path: str) -> List[Tuple[str, int]]:
        """解析JSON文件 - 查找results数组"""
        targets = []
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 优先查找 results 数组格式: {"results":[{"ip":"xxx","port":"xxx"}]}
        if isinstance(data, dict) and 'results' in data:
            results = data['results']
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        host = item.get('ip') or item.get('host') or item.get('domain')
                        port = item.get('port', 11434)
                        
                        if host:
                            # 清理host
                            host = str(host).replace('http://', '').replace('https://', '')
                            if '/' in host:
                                host = host.split('/')[0]
                            if ':' in host and not port:
                                parts = host.split(':')
                                host = parts[0]
                                try:
                                    port = int(parts[1])
                                except:
                                    port = 11434
                            
                            try:
                                port = int(port)
                            except:
                                port = 11434
                            
                            targets.append((host, port))
                return targets
        
        # 如果不是标准格式，递归提取
        def extract_from_json(obj):
            if isinstance(obj, dict):
                # 尝试提取ip/port对
                if 'ip' in obj or 'host' in obj or 'domain' in obj:
                    host = obj.get('ip') or obj.get('host') or obj.get('domain')
                    port = obj.get('port', 11434)
                    if host:
                        host = str(host).replace('http://', '').replace('https://', '')
                        if '/' in host:
                            host = host.split('/')[0]
                        try:
                            port = int(port)
                        except:
                            port = 11434
                        targets.append((host, port))
                else:
                    for value in obj.values():
                        extract_from_json(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_json(item)
        
        extract_from_json(data)
        return targets
    
    @staticmethod
    def _extract_target(text: str) -> Optional[Tuple[str, int]]:
        """
        从文本中提取目标（域名/IP + 端口）
        支持多种格式：
        - domain.com:11434
        - http://domain.com:11434
        - 192.168.1.1:11434
        - domain.com (默认端口11434)
        """
        text = text.strip()
        if not text:
            return None
        
        # 匹配 URL 格式
        url_pattern = r'(?:https?://)?([a-zA-Z0-9.-]+|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)'
        match = re.search(url_pattern, text)
        if match:
            host = match.group(1)
            port = int(match.group(2))
            return (host, port)
        
        # 匹配域名或IP（无端口，使用默认端口）
        host_pattern = r'^([a-zA-Z0-9.-]+|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$'
        match = re.match(host_pattern, text)
        if match:
            host = match.group(1)
            return (host, 11434)  # 默认端口
        
        return None
    
    @staticmethod
    def parse_ip_range(ip_range: str, port: int = 11434) -> List[Tuple[str, int]]:
        """
        解析IP段
        支持格式：
        - 192.168.1.1-192.168.1.254
        - 192.168.1.0/24
        - 192.168.1.1
        """
        targets = []
        
        # CIDR格式
        if '/' in ip_range:
            targets = DataParser._parse_cidr(ip_range, port)
        # 范围格式
        elif '-' in ip_range:
            targets = DataParser._parse_range(ip_range, port)
        # 单个IP
        else:
            if DataParser._is_valid_ip(ip_range):
                targets.append((ip_range, port))
        
        return targets
    
    @staticmethod
    def _parse_cidr(cidr: str, port: int) -> List[Tuple[str, int]]:
        """解析CIDR格式的IP段"""
        try:
            import ipaddress
            network = ipaddress.ip_network(cidr, strict=False)
            return [(str(ip), port) for ip in network.hosts()]
        except Exception:
            return []
    
    @staticmethod
    def _parse_range(ip_range: str, port: int) -> List[Tuple[str, int]]:
        """解析IP范围格式"""
        try:
            start_ip, end_ip = ip_range.split('-')
            start_ip = start_ip.strip()
            end_ip = end_ip.strip()
            
            # 如果end_ip只是最后一段，补全前面的部分
            if '.' not in end_ip:
                parts = start_ip.split('.')
                end_ip = '.'.join(parts[:3]) + '.' + end_ip
            
            import ipaddress
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)
            
            targets = []
            current = start
            while current <= end:
                targets.append((str(current), port))
                current += 1
            
            return targets
        except Exception:
            return []
    
    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """验证IP地址是否有效"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
