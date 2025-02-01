import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
from queue import Queue
from itertools import permutations

# @author：ispxx

class GitHubCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub用户名检测工具")
        self.root.geometry("1000x800")

        # 状态变量
        self.running = False
        self.queue = Queue()
        self.results = {"available": [], "unavailable": [], "errors": []}

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        # 输入字母生成衍生词区域
        input_frame = ttk.LabelFrame(self.root, text="输入字母生成衍生词")
        input_frame.pack(pady=10, padx=10, fill="x")

        self.input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.input_var, width=50).grid(row=0, column=0, padx=5)
        ttk.Button(input_frame, text="生成五位字母", command=lambda: self.generate_words(5)).grid(row=0, column=1)
        ttk.Button(input_frame, text="生成六位字母", command=lambda: self.generate_words(6)).grid(row=0, column=2)
        ttk.Button(input_frame, text="检测衍生词", command=self.check_generated_words).grid(row=0, column=3)

        # 文件选择区域
        file_frame = ttk.LabelFrame(self.root, text="文件操作")
        file_frame.pack(pady=10, padx=10, fill="x")

        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="选择文件", command=self.select_file).grid(row=0, column=1)
        ttk.Button(file_frame, text="开始检测", command=self.start_check).grid(row=0, column=2, padx=5)
        ttk.Button(file_frame, text="停止", command=self.stop_check).grid(row=0, column=3)

        # 进度显示
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(pady=5, fill="x", padx=10)

        self.status = ttk.Label(self.root, text="就绪")
        self.status.pack()

        # 结果展示
        result_frame = ttk.LabelFrame(self.root, text="检测结果")
        result_frame.pack(pady=10, fill="both", expand=True, padx=10)

        columns = ("username", "status")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        self.tree.heading("username", text="用户名")
        self.tree.heading("status", text="状态")
        self.tree.pack(fill="both", expand=True)

        # 结果导出
        export_frame = ttk.Frame(self.root)
        export_frame.pack(pady=10)
        ttk.Button(export_frame, text="导出可用", command=lambda: self.export_results("available")).grid(row=0,
                                                                                                         column=0)
        ttk.Button(export_frame, text="导出不可用", command=lambda: self.export_results("unavailable")).grid(row=0,
                                                                                                             column=1)
        ttk.Button(export_frame, text="导出错误", command=lambda: self.export_results("errors")).grid(row=0, column=2)

    def select_file(self):
        file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        self.file_path.set(file)

    def generate_words(self, length):
        letters = self.input_var.get().strip()
        if not letters:
            messagebox.showerror("错误", "请输入字母")
            return

        # 生成指定长度的衍生词
        words = set()
        for p in permutations(letters, length):
            word = "".join(p)
            words.add(word)

        # 显示生成的衍生词
        self.results = {"available": [], "unavailable": [], "errors": []}
        self.tree.delete(*self.tree.get_children())
        for word in words:
            self.tree.insert("", "end", values=(word, "待检测"))

        self.status.config(text=f"已生成 {len(words)} 个{length}位衍生词")

    def check_generated_words(self):
        # 获取待检测的衍生词
        words = [self.tree.item(item, "values")[0] for item in self.tree.get_children()]
        if not words:
            messagebox.showerror("错误", "没有可检测的衍生词")
            return

        self.running = True
        self.results = {"available": [], "unavailable": [], "errors": []}

        # 创建检测线程
        self.worker = threading.Thread(target=self.run_check, args=(words,))
        self.worker.start()
        self.update_progress()

    def start_check(self):
        if not self.file_path.get():
            messagebox.showerror("错误", "请先选择用户名文件")
            return

        try:
            with open(self.file_path.get(), "r") as f:
                usernames = [line.strip() for line in f if line.strip()]
        except Exception as e:
            messagebox.showerror("错误", f"文件读取失败: {str(e)}")
            return

        self.running = True
        self.results = {"available": [], "unavailable": [], "errors": []}
        self.tree.delete(*self.tree.get_children())

        # 创建检测线程
        self.worker = threading.Thread(target=self.run_check, args=(usernames,))
        self.worker.start()
        self.update_progress()

    def run_check(self, usernames):
        total = len(usernames)
        for idx, username in enumerate(usernames, 1):
            if not self.running:
                break
            try:
                url = f"https://github.com/{username}"
                # 禁用SSL验证
                response = requests.head(url, timeout=5, verify=False)
                if response.status_code == 404:
                    status = "可用"
                    self.results["available"].append(username)
                else:
                    status = "不可用"
                    self.results["unavailable"].append(username)
                self.queue.put((username, status, idx / total * 100))
            except Exception as e:
                self.results["errors"].append(f"{username}: {str(e)}")
                self.queue.put((username, f"错误: {str(e)}", idx / total * 100))

    def update_progress(self):
        while not self.queue.empty():
            username, status, progress = self.queue.get()

            # 更新结果
            if "可用" in status:
                tag = "success"
            elif "不可用" in status:
                tag = "error"
            else:
                tag = "warning"

            # 更新Treeview中的状态
            for item in self.tree.get_children():
                if self.tree.item(item, "values")[0] == username:
                    self.tree.item(item, values=(username, status), tags=(tag,))
                    break

            self.progress["value"] = progress
            self.status.config(
                text=f"已检测: {len(self.results['available'])} 可用, {len(self.results['unavailable'])} 不可用")

        if self.running:
            self.root.after(100, self.update_progress)

    def stop_check(self):
        self.running = False
        self.status.config(text="检测已停止")

    def export_results(self, category):
        if not self.results[category]:
            messagebox.showinfo("提示", f"没有{category}的结果")
            return

        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if file:
            try:
                with open(file, "w", encoding="utf-8") as f:
                    if category == "errors":
                        f.write("\n".join(self.results[category]))
                    else:
                        f.write("\n".join(self.results[category]))
                messagebox.showinfo("成功", f"结果已导出到 {file}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubCheckerApp(root)

    # 配置样式
    style = ttk.Style()
    style.configure("success.Treeview", foreground="green")
    style.configure("error.Treeview", foreground="red")
    style.configure("warning.Treeview", foreground="orange")
    root.tk_setPalette(background="#f0f0f0")

    root.mainloop()
