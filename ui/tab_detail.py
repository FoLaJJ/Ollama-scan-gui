# -*- coding: utf-8 -*-
"""
详情Tab - 显示目标的详细信息和操作
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
from modules.ollama_scanner import OllamaScanner


class DetailTab:
    """详情Tab - 可关闭的动态Tab"""
    
    def __init__(self, parent, notebook, host, port, config, on_close_callback):
        self.parent = parent
        self.notebook = notebook
        self.host = host
        self.port = port
        self.config = config
        self.on_close_callback = on_close_callback
        
        # 创建Tab
        self.frame = ttk.Frame(notebook)
        self.tab_id = notebook.add(self.frame, text=f"📋 {host}:{port}")
        
        # 创建UI
        self.create_ui()
        
        # 切换到新Tab
        notebook.select(self.frame)
        
        # 自动加载基本信息
        self.load_basic_info()
    
    def create_ui(self):
        """创建UI"""
        # 顶部信息栏
        info_frame = ttk.LabelFrame(self.frame, text="目标信息", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(info_frame, text=f"目标: {self.host}:{self.port}", 
                 font=("", 11, "bold")).pack(anchor=tk.W)
        self.status_label = ttk.Label(info_frame, text="正在加载...", foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=2)
        
        # 关闭按钮
        close_btn = ttk.Button(info_frame, text="✖ 关闭此Tab", command=self.close_tab)
        close_btn.pack(side=tk.RIGHT)
        
        # 命令按钮区
        cmd_frame = ttk.LabelFrame(self.frame, text="命令操作", padding=10)
        cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        commands = [
            ("list", "📃 列出模型"),
            ("ps", "⚡️ 运行中的模型"),
            ("version", "📌 版本信息"),
            ("pull", "📥 拉取模型"),
            ("show", "🔍 模型详情"),
            ("rm", "🗑️ 删除模型"),
            ("chat", "💬 对话"),
        ]
        
        row, col = 0, 0
        for cmd, label in commands:
            btn = ttk.Button(cmd_frame, text=label, 
                           command=lambda c=cmd: self.execute_command(c))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky=tk.EW)
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        # 配置列权重
        for i in range(4):
            cmd_frame.columnconfigure(i, weight=1)
        
        # 输出区域
        output_frame = ttk.LabelFrame(self.frame, text="输出", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=20, width=80, 
                                                     wrap=tk.NONE, font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本标签样式
        self.output_text.tag_config("header", font=("Consolas", 10, "bold"), foreground="blue")
        self.output_text.tag_config("success", foreground="green")
        self.output_text.tag_config("error", foreground="red")
        self.output_text.tag_config("info", foreground="gray")
    
    def close_tab(self):
        """关闭Tab"""
        self.notebook.forget(self.frame)
        if self.on_close_callback:
            self.on_close_callback(self)
    
    def load_basic_info(self):
        """加载基本信息"""
        def run():
            timeout = self.config.get("scan", {}).get("timeout", 5)
            scanner = OllamaScanner(timeout=timeout)
            result = scanner.scan_single(self.host, self.port)
            
            self.frame.after(0, lambda: self.show_basic_info(result))
        
        threading.Thread(target=run, daemon=True).start()
    
    def show_basic_info(self, result):
        """显示基本信息"""
        if result.vulnerable:
            self.status_label.config(text=f"✅ 未授权访问 | 版本: {result.version} | 模型数: {len(result.models)}", 
                                    foreground="green")
            self.output_text.insert(tk.END, "=== 基本信息 ===\n", "header")
            self.output_text.insert(tk.END, f"状态: 未授权访问\n", "success")
            self.output_text.insert(tk.END, f"版本: {result.version}\n")
            self.output_text.insert(tk.END, f"模型数量: {len(result.models)}\n")
            if result.models:
                self.output_text.insert(tk.END, f"模型列表: {', '.join(result.models[:5])}\n")
                if len(result.models) > 5:
                    self.output_text.insert(tk.END, f"... 还有 {len(result.models)-5} 个模型\n", "info")
            self.output_text.insert(tk.END, "\n")
        else:
            self.status_label.config(text=f"❌ 连接失败: {result.error}", foreground="red")
            self.output_text.insert(tk.END, "=== 连接失败 ===\n", "header")
            self.output_text.insert(tk.END, f"错误: {result.error}\n", "error")
            self.output_text.insert(tk.END, "\n")
    
    def execute_command(self, command):
        """执行命令"""
        if command in ["pull", "show", "rm"]:
            # 需要输入模型名称
            self.show_model_input_dialog(command)
        elif command == "chat":
            self.start_chat()
        else:
            # 直接执行
            self.run_command(command)
    
    def show_model_input_dialog(self, command):
        """显示模型名称输入对话框"""
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"输入模型名称 - {command}")
        dialog.geometry("400x150")
        dialog.transient(self.frame)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"请输入模型名称:", font=("", 10)).pack(pady=10)
        
        model_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=model_var, width=40)
        entry.pack(pady=5)
        entry.focus()
        
        def on_ok():
            model_name = model_var.get().strip()
            if model_name:
                dialog.destroy()
                self.run_command(command, model_name)
            else:
                messagebox.showwarning("警告", "请输入模型名称")
        
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        entry.bind("<Return>", lambda e: on_ok())
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
    
    def run_command(self, command, model_name=None):
        """运行命令"""
        self.output_text.insert(tk.END, f"\n=== 执行命令: {command}", "header")
        if model_name:
            self.output_text.insert(tk.END, f" {model_name}", "header")
        self.output_text.insert(tk.END, " ===\n", "header")
        self.output_text.see(tk.END)
        
        def run():
            timeout = self.config.get("scan", {}).get("timeout", 30 if command == "pull" else 5)
            scanner = OllamaScanner(timeout=timeout)
            result = scanner.execute_command(self.host, self.port, command, model_name)
            
            self.frame.after(0, lambda: self.show_command_result(command, result))
        
        threading.Thread(target=run, daemon=True).start()
    
    def show_command_result(self, command, result):
        """显示命令结果"""
        if result.get("success"):
            data = result.get("data")
            
            if command == "list":
                # 显示模型列表表格
                self.show_model_table(data)
            elif command == "ps":
                # 显示运行中的模型
                self.show_running_models(data)
            else:
                # 其他命令显示JSON
                self.output_text.insert(tk.END, json.dumps(data, indent=2, ensure_ascii=False) + "\n", "success")
        else:
            self.output_text.insert(tk.END, f"错误: {result.get('error')}\n", "error")
        
        self.output_text.insert(tk.END, "\n")
        self.output_text.see(tk.END)
    
    def show_model_table(self, models):
        """显示模型列表表格"""
        if not models:
            self.output_text.insert(tk.END, "没有可用的模型\n", "info")
            return
        
        # 表头 - 使用固定宽度
        header = f"{'模型名称':<45}{'大小':<15}{'格式':<12}{'参数量':<15}{'量化等级':<15}\n"
        self.output_text.insert(tk.END, header, "header")
        self.output_text.insert(tk.END, "=" * 110 + "\n", "info")
        
        # 数据行
        for model in models:
            name = model.get('name', 'Unknown')
            if len(name) > 43:
                name = name[:40] + "..."
            
            size = model.get('size', 0)
            if size:
                if size >= 1024**3:
                    size_str = f"{size / (1024**3):.2f} GB"
                elif size >= 1024**2:
                    size_str = f"{size / (1024**2):.2f} MB"
                else:
                    size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = "Unknown"
            
            details = model.get('details', {})
            format_str = details.get('format', 'Unknown') if details else 'Unknown'
            param_size = details.get('parameter_size', 'Unknown') if details else 'Unknown'
            quant_level = details.get('quantization_level', 'Unknown') if details else 'Unknown'
            
            line = f"{name:<45}{size_str:<15}{format_str:<12}{str(param_size):<15}{str(quant_level):<15}\n"
            self.output_text.insert(tk.END, line)
    
    def show_running_models(self, models):
        """显示运行中的模型"""
        if not models:
            self.output_text.insert(tk.END, "没有运行中的模型\n", "info")
            return
        
        # 表头
        header = f"{'模型名称':<45}{'大小':<15}{'过期时间':<30}\n"
        self.output_text.insert(tk.END, header, "header")
        self.output_text.insert(tk.END, "=" * 95 + "\n", "info")
        
        # 数据行
        for model in models:
            name = model.get('name', 'Unknown')
            if len(name) > 43:
                name = name[:40] + "..."
            
            size = model.get('size', 0)
            if size:
                if size >= 1024**3:
                    size_str = f"{size / (1024**3):.2f} GB"
                elif size >= 1024**2:
                    size_str = f"{size / (1024**2):.2f} MB"
                else:
                    size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = "Unknown"
            
            expires = model.get('expires_at', 'Unknown')
            
            line = f"{name:<45}{size_str:<15}{str(expires):<30}\n"
            self.output_text.insert(tk.END, line)
    
    def start_chat(self):
        """启动对话功能"""
        # 首先获取模型列表
        self.output_text.insert(tk.END, "\n=== 启动对话 ===\n", "header")
        self.output_text.insert(tk.END, "正在获取模型列表...\n", "info")
        
        def get_models():
            timeout = self.config.get("scan", {}).get("timeout", 5)
            scanner = OllamaScanner(timeout=timeout)
            result = scanner.execute_command(self.host, self.port, "list")
            
            self.frame.after(0, lambda: self.show_chat_dialog(result))
        
        threading.Thread(target=get_models, daemon=True).start()
    
    def show_chat_dialog(self, models_result):
        """显示对话窗口"""
        if not models_result.get("success"):
            self.output_text.insert(tk.END, f"获取模型列表失败: {models_result.get('error')}\n", "error")
            return
        
        models = models_result.get("data", [])
        if not models:
            self.output_text.insert(tk.END, "没有可用的模型\n", "error")
            return
        
        # 创建对话窗口
        chat_window = tk.Toplevel(self.frame)
        chat_window.title(f"对话 - {self.host}:{self.port}")
        chat_window.geometry("700x600")
        
        # 模型选择
        top_frame = ttk.Frame(chat_window, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="选择模型:").pack(side=tk.LEFT, padx=5)
        model_var = tk.StringVar()
        model_names = [m.get('name', '') for m in models]
        model_combo = ttk.Combobox(top_frame, textvariable=model_var, values=model_names, width=40)
        model_combo.pack(side=tk.LEFT, padx=5)
        if model_names:
            model_combo.set(model_names[0])
        
        # 对话历史
        history_frame = ttk.LabelFrame(chat_window, text="对话历史", padding=5)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        history_text = scrolledtext.ScrolledText(history_frame, height=20, wrap=tk.WORD)
        history_text.pack(fill=tk.BOTH, expand=True)
        history_text.tag_config("user", foreground="blue", font=("", 10, "bold"))
        history_text.tag_config("ai", foreground="green")
        
        # 输入区
        input_frame = ttk.Frame(chat_window, padding=10)
        input_frame.pack(fill=tk.X)
        
        input_text = tk.Text(input_frame, height=3, wrap=tk.WORD)
        input_text.pack(fill=tk.X, pady=5)
        
        def send_message():
            message = input_text.get("1.0", tk.END).strip()
            if not message:
                return
            
            model_name = model_var.get()
            if not model_name:
                messagebox.showwarning("警告", "请选择模型")
                return
            
            # 显示用户消息
            history_text.insert(tk.END, f"👤 你: {message}\n", "user")
            history_text.see(tk.END)
            input_text.delete("1.0", tk.END)
            
            # 发送请求
            def chat():
                try:
                    import requests
                    url = f"http://{self.host}:{self.port}/api/chat"
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": message}],
                        "stream": False
                    }
                    response = requests.post(url, json=payload, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        reply = data.get("message", {}).get("content", "无响应")
                        chat_window.after(0, lambda: show_reply(reply))
                    else:
                        chat_window.after(0, lambda: show_reply(f"错误: HTTP {response.status_code}"))
                except Exception as e:
                    chat_window.after(0, lambda: show_reply(f"错误: {str(e)}"))
            
            def show_reply(reply):
                history_text.insert(tk.END, f"🤖 AI: {reply}\n\n", "ai")
                history_text.see(tk.END)
            
            threading.Thread(target=chat, daemon=True).start()
        
        send_btn = ttk.Button(input_frame, text="发送", command=send_message)
        send_btn.pack()
        
        # 绑定回车发送
        input_text.bind("<Control-Return>", lambda e: send_message())
        
        self.output_text.insert(tk.END, "对话窗口已打开\n", "success")
