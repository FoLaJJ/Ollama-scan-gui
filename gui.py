# -*- coding: utf-8 -*-
"""
Ollama扫描工具 - 主GUI程序（重构版）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import yaml
from datetime import datetime

# 导入自定义模块
from modules.data_parser import DataParser
from modules.ollama_scanner import OllamaScanner
from modules.exporter import ResultExporter
from ui.tab_file_scan import FileScanTab
from ui.tab_detail import DetailTab


class OllamaScanGUI:
    """Ollama扫描工具主界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🔍 Ollama扫描验证工具 v2.0")
        
        # 加载配置
        self.config = self.load_config()
        
        # 设置窗口大小和居中
        window_width = self.config.get("gui", {}).get("window_width", 1200)
        window_height = self.config.get("gui", {}).get("window_height", 800)
        
        # 计算居中位置
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置最小窗口大小
        self.root.minsize(1000, 600)
        
        # 配置样式
        self.setup_styles()
        
        # 扫描相关变量
        self.scan_results = []
        self.scanning = False
        self.stop_scan = False
        self.scanner = None
        
        # 详情Tab管理
        self.detail_tabs = []
        
        # 创建UI
        self.create_widgets()
        
        # 确保result目录存在
        result_path = self.config.get("export", {}).get("default_path", "./result")
        if not os.path.exists(result_path):
            os.makedirs(result_path)
    
    def load_config(self):
        """加载配置文件"""
        config_path = "config.yaml"
        
        if getattr(sys, 'frozen', False):
            config_path = os.path.join(os.path.dirname(sys.executable), "config.yaml")
        
        if not os.path.exists(config_path):
            default_config = {
                "scan": {"default_port": 11434, "default_threads": 10, "timeout": 5},
                "export": {"default_path": "./result", "default_format": "csv"},
                "gui": {"window_width": 1200, "window_height": 800}
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        
        # 使用更现代的主题
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        
        # 自定义样式
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 11, 'bold'))
        style.configure('Info.TLabel', font=('Microsoft YaHei UI', 9))
        style.configure('Success.TLabel', foreground='#28a745', font=('Microsoft YaHei UI', 10, 'bold'))
        style.configure('Error.TLabel', foreground='#dc3545', font=('Microsoft YaHei UI', 10))
        
        # 按钮样式
        style.configure('Accent.TButton', font=('Microsoft YaHei UI', 9, 'bold'))
        
        # Notebook样式
        style.configure('TNotebook.Tab', font=('Microsoft YaHei UI', 10), padding=[15, 8])
        
        # Treeview样式
        style.configure('Treeview', font=('Microsoft YaHei UI', 9), rowheight=25)
        style.configure('Treeview.Heading', font=('Microsoft YaHei UI', 9, 'bold'))
    
    def create_widgets(self):
        """创建界面组件"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 功能一：文件导入扫描
        tab1_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab1_frame, text="📁 文件导入扫描")
        self.tab1 = FileScanTab(tab1_frame, self.config, self.start_scan, 
                               self.clear_results, self.export_results)
        
        # 设置停止按钮回调
        self.tab1.stop_btn.config(command=self.stop_scanning)
        
        # 绑定双击事件
        self.tab1.tree.bind("<Double-1>", lambda e: self.on_result_double_click(self.tab1.tree))
        
        # 功能二：IP段扫描（简化版，类似功能一）
        tab2_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab2_frame, text="🌐 IP段扫描")
        self.create_tab2(tab2_frame)
        
        # 功能三：本地验证
        tab3_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab3_frame, text="🏠 本地验证")
        self.create_tab3(tab3_frame)
    
    def create_tab2(self, parent):
        """创建IP段扫描Tab"""
        # 控制面板
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="IP段:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.ip_range_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.ip_range_var, width=30).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(control_frame, text="(支持: 192.168.1.1-254, 192.168.1.0/24)").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(control_frame, text="端口:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.port_var = tk.IntVar(value=self.config.get("scan", {}).get("default_port", 11434))
        ttk.Entry(control_frame, textvariable=self.port_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(control_frame, text="线程数:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.threads_var2 = tk.IntVar(value=self.config.get("scan", {}).get("default_threads", 10))
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.threads_var2, width=10).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        self.scan_btn2 = ttk.Button(button_frame, text="开始扫描", command=lambda: self.start_scan(2))
        self.scan_btn2.pack(side=tk.LEFT, padx=5)
        self.stop_btn2 = ttk.Button(button_frame, text="停止扫描", command=self.stop_scanning, state=tk.DISABLED)
        self.stop_btn2.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", command=lambda: self.clear_results(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出结果", command=lambda: self.export_results(2)).pack(side=tk.LEFT, padx=5)
        
        self.progress2 = ttk.Progressbar(parent, mode='determinate')
        self.progress2.pack(fill=tk.X, padx=5, pady=2)
        self.status_label2 = ttk.Label(parent, text="就绪")
        self.status_label2.pack(fill=tk.X, padx=5)
        
        self.create_result_tree(parent, 2)
    
    def create_tab3(self, parent):
        """创建本地验证Tab"""
        control_frame = ttk.LabelFrame(parent, text="本地Ollama验证", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="地址:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.local_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(control_frame, textvariable=self.local_host_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(control_frame, text="端口:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.local_port_var = tk.IntVar(value=11434)
        ttk.Entry(control_frame, textvariable=self.local_port_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Button(control_frame, text="打开详情页", command=self.open_local_detail).grid(row=0, column=4, padx=5)
        
        ttk.Label(parent, text="\n提示: 点击上方按钮打开本地Ollama的详情页，可以执行所有命令操作", 
                 font=("", 10), foreground="gray").pack(pady=20)
    
    def create_result_tree(self, parent, tab_num):
        """创建结果表格"""
        result_frame = ttk.LabelFrame(parent, text="扫描结果（双击查看详情）", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("host", "port", "status", "version", "models", "error", "time")
        tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)
        
        tree.heading("host", text="主机")
        tree.heading("port", text="端口")
        tree.heading("status", text="状态")
        tree.heading("version", text="版本")
        tree.heading("models", text="模型")
        tree.heading("error", text="错误信息")
        tree.heading("time", text="时间")
        
        tree.column("host", width=150)
        tree.column("port", width=60)
        tree.column("status", width=100)
        tree.column("version", width=100)
        tree.column("models", width=200)
        tree.column("error", width=150)
        tree.column("time", width=150)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件
        tree.bind("<Double-1>", lambda e: self.on_result_double_click(tree))
        
        if tab_num == 2:
            self.tree2 = tree
    
    def on_result_double_click(self, tree):
        """双击结果行打开详情Tab"""
        selection = tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = tree.item(item, 'values')
        
        # 只有未授权访问的才能打开详情
        if not values[2].startswith("✅"):
            messagebox.showinfo("提示", "只有未授权访问的目标才能查看详情")
            return
        
        host = values[0]
        port = int(values[1])
        
        # 检查是否已经打开
        for detail_tab in self.detail_tabs:
            if detail_tab.host == host and detail_tab.port == port:
                self.notebook.select(detail_tab.frame)
                return
        
        # 创建新的详情Tab
        detail_tab = DetailTab(self.root, self.notebook, host, port, self.config, 
                              self.on_detail_tab_close)
        self.detail_tabs.append(detail_tab)
    
    def on_detail_tab_close(self, detail_tab):
        """详情Tab关闭回调"""
        if detail_tab in self.detail_tabs:
            self.detail_tabs.remove(detail_tab)
    
    def open_local_detail(self):
        """打开本地详情页"""
        host = self.local_host_var.get()
        port = self.local_port_var.get()
        
        # 检查是否已经打开
        for detail_tab in self.detail_tabs:
            if detail_tab.host == host and detail_tab.port == port:
                self.notebook.select(detail_tab.frame)
                return
        
        # 创建新的详情Tab
        detail_tab = DetailTab(self.root, self.notebook, host, port, self.config, 
                              self.on_detail_tab_close)
        self.detail_tabs.append(detail_tab)
    
    def start_scan(self, tab):
        """开始扫描"""
        if self.scanning:
            messagebox.showwarning("警告", "扫描正在进行中")
            return
        
        if tab == 1:
            if not hasattr(self.tab1, 'parsed_targets') or not self.tab1.parsed_targets:
                messagebox.showwarning("警告", "请先解析文件")
                return
            
            start = self.tab1.start_index_var.get()
            end = self.tab1.end_index_var.get()
            
            if end == 0:
                end = len(self.tab1.parsed_targets)
            
            if start < 0 or end > len(self.tab1.parsed_targets) or start >= end:
                messagebox.showwarning("警告", "扫描范围无效")
                return
            
            targets = self.tab1.parsed_targets[start:end]
            threads = self.tab1.threads_var.get()
            tree = self.tab1.tree
            progress = self.tab1.progress
            status_label = self.tab1.status_label
            scan_btn = self.tab1.scan_btn
            stop_btn = self.tab1.stop_btn
            
        else:  # tab == 2
            ip_range = self.ip_range_var.get()
            if not ip_range:
                messagebox.showwarning("警告", "请输入IP段")
                return
            
            port = self.port_var.get()
            try:
                targets = DataParser.parse_ip_range(ip_range, port)
                if not targets:
                    messagebox.showwarning("警告", "无法解析IP段")
                    return
            except Exception as e:
                messagebox.showerror("错误", f"解析IP段失败: {str(e)}")
                return
            
            threads = self.threads_var2.get()
            tree = self.tree2
            progress = self.progress2
            status_label = self.status_label2
            scan_btn = self.scan_btn2
            stop_btn = self.stop_btn2
        
        # 清空之前的结果
        for item in tree.get_children():
            tree.delete(item)
        self.scan_results = []
        
        # 更新UI状态
        scan_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.NORMAL)
        progress['value'] = 0
        progress['maximum'] = len(targets)
        status_label.config(text=f"准备扫描 {len(targets)} 个目标...")
        
        # 启动扫描线程
        self.scanning = True
        self.stop_scan = False
        
        def scan_thread():
            timeout = self.config.get("scan", {}).get("timeout", 5)
            self.scanner = OllamaScanner(timeout=timeout)
            
            def callback(result, current, total):
                if not self.stop_scan:
                    self.root.after(0, lambda: self.update_scan_result(
                        result, current, total, tree, progress, status_label))
            
            def stop_flag():
                return self.stop_scan
            
            self.scanner.scan_batch(targets, threads, callback, stop_flag)
            
            self.root.after(0, lambda: self.scan_finished(scan_btn, stop_btn, status_label))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def update_scan_result(self, result, current, total, tree, progress, status_label):
        """更新扫描结果"""
        self.scan_results.append(result)
        
        status = "✅ 未授权访问" if result.vulnerable else "❌ 无法访问"
        models_str = ", ".join(result.models[:3]) if result.models else ""
        if len(result.models) > 3:
            models_str += f" (+{len(result.models)-3})"
        
        values = (result.host, result.port, status, result.version, models_str, result.error, result.timestamp)
        
        item = tree.insert("", tk.END, values=values)
        
        if result.vulnerable:
            tree.item(item, tags=('vulnerable',))
            tree.tag_configure('vulnerable', background='#90EE90')
        
        progress['value'] = current
        vulnerable_count = sum(1 for r in self.scan_results if r.vulnerable)
        status_label.config(text=f"扫描进度: {current}/{total} - 发现未授权访问: {vulnerable_count}")
        
        tree.see(item)
    
    def scan_finished(self, scan_btn, stop_btn, status_label):
        """扫描完成"""
        self.scanning = False
        scan_btn.config(state=tk.NORMAL)
        stop_btn.config(state=tk.DISABLED)
        
        vulnerable_count = sum(1 for r in self.scan_results if r.vulnerable)
        status_label.config(text=f"扫描完成！共扫描 {len(self.scan_results)} 个目标，发现 {vulnerable_count} 个未授权访问")
    
    def stop_scanning(self):
        """停止扫描"""
        if self.scanning:
            self.stop_scan = True
            messagebox.showinfo("提示", "正在停止扫描...")
    
    def clear_results(self, tab):
        """清空结果"""
        tree = self.tab1.tree if tab == 1 else self.tree2
        for item in tree.get_children():
            tree.delete(item)
        self.scan_results = []
        
        status_label = self.tab1.status_label if tab == 1 else self.status_label2
        status_label.config(text="就绪")
    
    def export_results(self, tab):
        """导出结果"""
        if not self.scan_results:
            messagebox.showwarning("警告", "没有可导出的结果")
            return
        
        export_window = tk.Toplevel(self.root)
        export_window.title("导出设置")
        export_window.geometry("400x250")
        
        ttk.Label(export_window, text="导出格式:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        format_var = tk.StringVar(value="csv")
        ttk.Radiobutton(export_window, text="CSV", variable=format_var, value="csv").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(export_window, text="JSON", variable=format_var, value="json").grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(export_window, text="Excel", variable=format_var, value="excel").grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(export_window, text="导出范围:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        export_all_var = tk.BooleanVar(value=True)
        ttk.Radiobutton(export_window, text="全部", variable=export_all_var, value=True).grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(export_window, text="仅未授权", variable=export_all_var, value=False).grid(row=1, column=2, sticky=tk.W)
        
        ttk.Label(export_window, text="文件名:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        filename_var = tk.StringVar(value=f"scan_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        ttk.Entry(export_window, textvariable=filename_var, width=30).grid(row=2, column=1, columnspan=3, padx=5, sticky=tk.W)
        
        def do_export():
            format_type = format_var.get()
            vulnerable_only = not export_all_var.get()
            filename = filename_var.get()
            
            results_to_export = [r.to_dict() for r in self.scan_results]
            if vulnerable_only:
                results_to_export = ResultExporter.filter_results(results_to_export, vulnerable_only=True)
            
            if not results_to_export:
                messagebox.showwarning("警告", "没有符合条件的结果")
                return
            
            default_path = self.config.get("export", {}).get("default_path", "./result")
            file_path = os.path.join(default_path, filename)
            
            success = ResultExporter.export(results_to_export, file_path, format_type)
            
            if success:
                messagebox.showinfo("成功", f"成功导出 {len(results_to_export)} 条结果到:\n{file_path}")
                export_window.destroy()
            else:
                messagebox.showerror("错误", "导出失败")
        
        ttk.Button(export_window, text="导出", command=do_export).grid(row=3, column=1, columnspan=2, pady=20)


def main():
    root = tk.Tk()
    app = OllamaScanGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
