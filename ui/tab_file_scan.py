# -*- coding: utf-8 -*-
"""
功能一：文件导入扫描Tab
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from modules.data_parser import DataParser


class FileScanTab:
    """文件导入扫描Tab"""
    
    def __init__(self, parent, config, start_scan_callback, clear_results_callback, export_results_callback):
        self.parent = parent
        self.config = config
        self.start_scan_callback = start_scan_callback
        self.clear_results_callback = clear_results_callback
        self.export_results_callback = export_results_callback
        self.parsed_targets = []
        
        self.create_ui()
    
    def create_ui(self):
        """创建UI"""
        # 控制面板
        control_frame = ttk.LabelFrame(self.parent, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件选择
        ttk.Label(control_frame, text="文件:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.file_path_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.file_path_var, width=50).grid(
            row=0, column=1, padx=5, pady=2)
        ttk.Button(control_frame, text="选择文件", command=self.select_file).grid(
            row=0, column=2, padx=5)
        ttk.Button(control_frame, text="解析文件", command=self.parse_file).grid(
            row=0, column=3, padx=5)
        
        # 扫描设置
        ttk.Label(control_frame, text="线程数:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.threads_var = tk.IntVar(value=self.config.get("scan", {}).get("default_threads", 10))
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.threads_var, 
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(control_frame, text="扫描范围:").grid(row=1, column=2, sticky=tk.W, padx=5)
        range_frame = ttk.Frame(control_frame)
        range_frame.grid(row=1, column=3, columnspan=2, sticky=tk.W, padx=5)
        self.start_index_var = tk.IntVar(value=0)
        self.end_index_var = tk.IntVar(value=0)
        ttk.Entry(range_frame, textvariable=self.start_index_var, width=8).pack(side=tk.LEFT)
        ttk.Label(range_frame, text="-").pack(side=tk.LEFT, padx=2)
        ttk.Entry(range_frame, textvariable=self.end_index_var, width=8).pack(side=tk.LEFT)
        
        # 按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=5, pady=10)
        self.scan_btn = ttk.Button(button_frame, text="开始扫描", 
                                   command=lambda: self.start_scan_callback(1))
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(button_frame, text="停止扫描", 
                                   command=None, state=tk.DISABLED)  # 回调将在主GUI中设置
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空结果", 
                  command=lambda: self.clear_results_callback(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导出结果", 
                  command=lambda: self.export_results_callback(1)).pack(side=tk.LEFT, padx=5)
        
        # 进度显示
        self.progress = ttk.Progressbar(self.parent, mode='determinate')
        self.progress.pack(fill=tk.X, padx=5, pady=2)
        self.status_label = ttk.Label(self.parent, text="就绪")
        self.status_label.pack(fill=tk.X, padx=5)
        
        # 结果表格
        self.create_result_tree()
    
    def create_result_tree(self):
        """创建结果表格"""
        result_frame = ttk.LabelFrame(self.parent, text="扫描结果（双击查看详情）", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("host", "port", "status", "version", "models", "error", "time")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("host", text="主机")
        self.tree.heading("port", text="端口")
        self.tree.heading("status", text="状态")
        self.tree.heading("version", text="版本")
        self.tree.heading("models", text="模型")
        self.tree.heading("error", text="错误信息")
        self.tree.heading("time", text="时间")
        
        self.tree.column("host", width=150)
        self.tree.column("port", width=60)
        self.tree.column("status", width=100)
        self.tree.column("version", width=100)
        self.tree.column("models", width=200)
        self.tree.column("error", width=150)
        self.tree.column("time", width=150)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def select_file(self):
        """选择文件"""
        filetypes = (
            ("所有支持的文件", "*.csv *.json"),
            ("CSV文件", "*.csv"),
            ("JSON文件", "*.json"),
        )
        filename = filedialog.askopenfilename(title="选择文件", filetypes=filetypes)
        if filename:
            self.file_path_var.set(filename)
    
    def parse_file(self):
        """解析文件并显示预览"""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请先选择文件")
            return
        
        try:
            targets = DataParser.parse_file(file_path)
            self.parsed_targets = targets
            self.end_index_var.set(len(targets))
            
            # 显示预览窗口
            self.show_preview(targets, file_path)
            
        except Exception as e:
            messagebox.showerror("错误", f"解析文件失败: {str(e)}")
    
    def show_preview(self, targets, file_path):
        """显示解析预览窗口"""
        preview_window = tk.Toplevel(self.parent)
        preview_window.title(f"解析预览 - {file_path.split('/')[-1]}")
        preview_window.geometry("700x500")
        
        # 顶部信息
        info_frame = ttk.Frame(preview_window, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text=f"文件: {file_path}", font=("", 10)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"解析结果: 共 {len(targets)} 个目标", 
                 font=("", 10, "bold"), foreground="green").pack(anchor=tk.W, pady=5)
        
        # 预览表格
        table_frame = ttk.Frame(preview_window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("index", "host", "port")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        tree.heading("index", text="序号")
        tree.heading("host", text="主机/IP")
        tree.heading("port", text="端口")
        
        tree.column("index", width=60)
        tree.column("host", width=400)
        tree.column("port", width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据（最多显示前100条）
        for idx, (host, port) in enumerate(targets[:100], 1):
            tree.insert("", tk.END, values=(idx, host, port))
        
        if len(targets) > 100:
            tree.insert("", tk.END, values=("...", f"还有 {len(targets)-100} 条数据", "..."))
        
        # 按钮
        btn_frame = ttk.Frame(preview_window, padding=10)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="确定", command=preview_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="复制到剪贴板", 
                  command=lambda: self.copy_to_clipboard(targets)).pack(side=tk.RIGHT, padx=5)
    
    def copy_to_clipboard(self, targets):
        """复制目标列表到剪贴板"""
        text = "\n".join([f"{host}:{port}" for host, port in targets])
        self.parent.clipboard_clear()
        self.parent.clipboard_append(text)
        messagebox.showinfo("成功", f"已复制 {len(targets)} 个目标到剪贴板")
