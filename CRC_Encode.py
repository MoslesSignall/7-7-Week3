# -*- coding: utf-8 -*-
"""
CRC 校验码生成器（3GPP TS 38.212）
- CRC-6 / CRC-11 / CRC-16 / CRC-24
- CRC-24 自动判断：≤8424 用 24A；>8424 用 24A + 分块 24B
- 导出时选择文件夹，自动命名
"""

import os
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime


# ============================================================
# 一、CRC 核心算法
# ============================================================
POLY_DEFS = {
    '6':   np.array([1, 1, 0, 0, 0, 0, 1], dtype=np.uint8),
    '11':  np.array([1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1], dtype=np.uint8),
    '16':  np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                    dtype=np.uint8),
    '24A': np.array([1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0,
                     0, 1, 1, 1, 1, 1, 0, 1, 1], dtype=np.uint8),
    '24B': np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 1, 1, 0, 0, 0, 1, 1], dtype=np.uint8),
}


def compute_crc_bits(bit_str, poly_key):
    """根据 01 字符串计算 CRC 校验位 (字符串长度 = 数据长度)"""
    if poly_key not in POLY_DEFS:
        raise ValueError(f"不支持的多项式: {poly_key}")

    gen_poly = POLY_DEFS[poly_key]
    L = len(gen_poly) - 1

    data = np.array([1 if c == '1' else 0 for c in bit_str], dtype=np.uint8)
    padded = np.concatenate([data, np.zeros(L, dtype=np.uint8)])

    for i in range(len(data)):
        if padded[i] == 1:
            padded[i:i + L + 1] ^= gen_poly

    return ''.join(str(b) for b in padded[-L:])


# ============================================================
# 二、分块规则
# ============================================================
BLOCK_SIZE = 8424


def plan_blocks(total_bits):
    """返回 (X, [l0, l1, ..., l_{X-1}])"""
    X = (total_bits + BLOCK_SIZE - 1) // BLOCK_SIZE
    base = total_bits // X
    rem = total_bits % X
    lengths = [(base + 1) if i < rem else base for i in range(X)]
    return X, lengths


def build_chunk_message(total_bits):
    if total_bits <= BLOCK_SIZE:
        return "将使用 CRC-24A（单文件导出）"
    X, lengths = plan_blocks(total_bits + 24)   # ★ 注意加 24 后分块
    parts = [f"第{i}块数据长度={l}，导出长度={l + 24}"
             for i, l in enumerate(lengths)]
    return (f"将使用 CRC-24A + 分块 CRC-24B，共 {X} 个文件：\n"
            + "\n".join(parts))


# ============================================================
# 三、可视化界面
# ============================================================
class CRCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CRC 校验码生成器（3GPP TS 38.212）")
        self.root.geometry("780x920")
        self.root.minsize(700, 700)
        self.root.resizable(True, True)

        self.bit_str = None
        self.file_bits = None
        self.file_path = None
        self.result_data = None

        self._build_ui()

    # --------------------------------------------------------
    def _build_ui(self):
        # ===== 底部按钮栏（先 pack，固定底部） =====
        f7 = tk.Frame(self.root)
        f7.pack(side="bottom", fill="x", padx=12, pady=(6, 12))

        self.btn_confirm = tk.Button(f7, text="确认并计算 CRC",
                                     width=18, height=2, state="disabled",
                                     command=self.confirm)
        self.btn_confirm.pack(side="left")

        self.btn_export = tk.Button(f7, text="导出到文件夹",
                                    width=18, height=2, state="disabled",
                                    command=self.export)
        self.btn_export.pack(side="left", padx=10)

        tk.Button(f7, text="退出", width=10, height=2,
                  command=self.root.destroy).pack(side="right")

        # ===== 顶部区域 =====

        # ① 选择文件
        f1 = tk.LabelFrame(self.root, text="① 选择文件（内容仅含 0/1）",
                           padx=10, pady=8)
        f1.pack(side="top", fill="x", padx=12, pady=6)
        tk.Button(f1, text="浏览文件…", width=14,
                  command=self.load_file).pack(side="left")
        self.lbl_file = tk.Label(f1, text="尚未选择文件",
                                 anchor="w", fg="gray")
        self.lbl_file.pack(side="left", padx=10, fill="x", expand=True)

        # ② 文件信息
        f2 = tk.LabelFrame(self.root, text="② 文件信息", padx=10, pady=8)
        f2.pack(side="top", fill="x", padx=12, pady=6)
        self.lbl_size = tk.Label(f2, text="长度: —", anchor="w",
                                 justify="left", font=("Consolas", 10))
        self.lbl_size.pack(fill="x")

        # ③ 内容预览
        f3 = tk.LabelFrame(self.root, text="③ 内容预览（前 256 字符）",
                           padx=10, pady=8)
        f3.pack(side="top", fill="x", padx=12, pady=6)
        self.txt_preview = tk.Text(f3, height=4, wrap="char",
                                   font=("Consolas", 9))
        self.txt_preview.pack(fill="both", expand=True)
        self.txt_preview.config(state="disabled")

        # ④ 选择 CRC（CRC-24 只有一个选项）
        f4 = tk.LabelFrame(self.root, text="④ 选择 CRC 方式",
                           padx=10, pady=8)
        f4.pack(side="top", fill="x", padx=12, pady=6)

        self.crc_options = ["CRC-6", "CRC-11", "CRC-16", "CRC-24"]
        self.crc_var = tk.StringVar(value="")
        self.crc_buttons = []

        row = tk.Frame(f4)
        row.pack(fill="x")
        for opt in self.crc_options:
            rb = tk.Radiobutton(row, text=opt, value=opt,
                                variable=self.crc_var,
                                command=self.on_crc_change)
            rb.pack(side="left", padx=10)
            self.crc_buttons.append(rb)

        # ⑤ 提示信息
        f5 = tk.LabelFrame(self.root, text="⑤ 提示信息", padx=10, pady=8)
        f5.pack(side="top", fill="both", expand=True, padx=12, pady=6)
        self.txt_msg = tk.Text(f5, height=6, wrap="word",
                               font=("Microsoft YaHei", 10))
        self.txt_msg.pack(fill="both", expand=True)
        self.txt_msg.config(state="disabled")

        # ⑥ 计算结果
        f6 = tk.LabelFrame(self.root, text="⑥ 计算结果", padx=10, pady=8)
        f6.pack(side="top", fill="both", expand=True, padx=12, pady=6)
        self.txt_result = tk.Text(f6, height=6, wrap="word",
                                  font=("Consolas", 9))
        self.txt_result.pack(fill="both", expand=True)
        self.txt_result.config(state="disabled")

    # --------------------------------------------------------
    def set_text(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    # --------------------------------------------------------
    def load_file(self):
        path = filedialog.askopenfilename(
            title="请选择 01 数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
        except Exception as e:
            messagebox.showerror("错误", f"读取失败:\n{e}")
            return

        bits = "".join(ch for ch in raw if ch in ("0", "1"))
        if not bits:
            messagebox.showerror("错误", "文件中没有有效的 0/1 数据")
            return

        self.file_path = path
        self.bit_str = bits
        self.file_bits = len(bits)
        self.result_data = None
        self.btn_export.config(state="disabled")

        self.lbl_file.config(text=os.path.basename(path), fg="black")
        self.lbl_size.config(
            text=(f"路径: {path}\n"
                  f"比特数: {self.file_bits:,} Bits（按 0/1 字符计数）")
        )
        self.set_text(self.txt_preview, bits[:256])
        self.set_text(self.txt_result, "")
        self.update_available_crc()

    # --------------------------------------------------------
    def update_available_crc(self):
        n = self.file_bits
        avail = []
        if 1 <= n <= 19:
            avail.append("CRC-6")
        if 20 <= n <= 39:
            avail.append("CRC-11")
        if n >= 40:
            avail.append("CRC-16")
        avail.append("CRC-24")   # 任意长度可用

        for rb in self.crc_buttons:
            rb.config(state="normal" if rb.cget("value") in avail
                                else "disabled")

        if avail:
            self.crc_var.set(avail[0])
        self.on_crc_change()

    # --------------------------------------------------------
    def on_crc_change(self):
        choice = self.crc_var.get()
        if not choice:
            self.btn_confirm.config(state="disabled")
            return

        if choice == "CRC-24":
            self.set_text(self.txt_msg,
                          build_chunk_message(self.file_bits))
        else:
            self.set_text(self.txt_msg,
                          f"将使用 {choice}（单文件导出）。")

        self.btn_confirm.config(state="normal")
        self.btn_export.config(state="disabled")
        self.result_data = None

    # --------------------------------------------------------
    def confirm(self):
        """确认 → 计算 → 准备导出内容"""
        choice = self.crc_var.get()
        if not choice:
            return

        n = self.file_bits
        bits = self.bit_str
        result_lines = []

        try:
            if choice == "CRC-24":
                if n <= BLOCK_SIZE:
                    # ===== 单文件：只用 CRC-24A =====
                    crc = compute_crc_bits(bits, '24A')
                    result_lines.append(f"[CRC-24A] 校验码: {crc}")

                    export_content = bits + crc
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    fname = f"{ts}_{len(export_content)}_CRC24_0.txt"

                    self.result_data = {
                        "mode": "single",
                        "files": [{"name": fname,
                                   "content": export_content}],
                    }

                else:
                    # ===== 多文件：先整块 CRC-24A，再分块 CRC-24B =====
                    crc24a = compute_crc_bits(bits, '24A')
                    combined = bits + crc24a       # 长度 = n + 24
                    result_lines.append(
                        f"[整块 CRC-24A] 校验码: {crc24a}  "
                        f"(数据+CRC总长={len(combined)})"
                    )

                    X, lengths = plan_blocks(len(combined))
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")

                    idx = 0
                    files = []
                    for i, ln in enumerate(lengths):
                        seg = combined[idx:idx + ln]
                        idx += ln
                        crc24b = compute_crc_bits(seg, '24B')
                        block_content = seg + crc24b   # 长度 = ln + 24

                        fname = (f"{ts}_{len(block_content)}"
                                 f"_CRC24_{i}.txt")
                        files.append({"name": fname,
                                      "content": block_content})

                        result_lines.append(
                            f"[第{i}块] 数据长={ln}, "
                            f"CRC-24B={crc24b}, "
                            f"导出长={len(block_content)} → {fname}"
                        )

                    self.result_data = {
                        "mode": "multi",
                        "crc24a": crc24a,
                        "files": files,
                    }

            else:
                # ===== CRC-6 / 11 / 16 =====
                key = choice.replace("CRC-", "")
                crc = compute_crc_bits(bits, key)
                result_lines.append(f"{choice} 校验码: {crc}")

                export_content = bits + crc
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                fname = f"{ts}_{len(export_content)}_{choice.replace('-', '')}_0.txt"

                self.result_data = {
                    "mode": "single",
                    "files": [{"name": fname,
                               "content": export_content}],
                }

        except Exception as e:
            messagebox.showerror("计算失败", str(e))
            return

        self.btn_export.config(state="normal")
        self.set_text(self.txt_result, "\n".join(result_lines))
        messagebox.showinfo(
            "完成",
            "CRC 计算完成。点击『导出到文件夹』选择保存位置。"
        )

    # --------------------------------------------------------
    def export(self):
        if not self.result_data:
            messagebox.showwarning("提示", "请先确认并计算 CRC")
            return

        # 只选文件夹
        out_dir = filedialog.askdirectory(title="请选择导出文件夹")
        if not out_dir:
            return

        try:
            written = []
            for item in self.result_data["files"]:
                full = os.path.join(out_dir, item["name"])
                with open(full, "w", encoding="utf-8") as f:
                    f.write(item["content"])
                written.append(item["name"])
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
            return

        messagebox.showinfo(
            "导出成功",
            f"共导出 {len(written)} 个文件到:\n{out_dir}\n\n"
            + "\n".join(written)
        )


# ============================================================
# 主入口0
# ============================================================
def main():
    root = tk.Tk()
    CRCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()