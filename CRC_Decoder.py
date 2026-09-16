# -*- coding: utf-8 -*-
"""
CRC 校验解码器（3GPP TS 38.212）
- 输入: 一个或多个已编码的 .txt 文件
- 文件名格式: 时间_长度_CRC方式_序号.txt
- 输出: 每个文件 / 每个包组的校验结果
"""

import os
import re
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from collections import defaultdict


# ============================================================
# 一、CRC 生成多项式（与编码器保持一致）
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


def crc_remainder(bit_str, poly_key):
    """
    计算 bit_str 对指定多项式做模 2 除的余数。
    - 传入的 bit_str 已经包含 CRC（不需要再补 0）
    - 返回余数 (字符串, 长度 = L)
    - 校验通过 ⇔ 余数为全 0
    """
    gen_poly = POLY_DEFS[poly_key]
    L = len(gen_poly) - 1

    data = np.array([1 if c == '1' else 0 for c in bit_str], dtype=np.uint8)

    # 直接做模 2 长除法（不补 0）
    for i in range(len(data) - L):
        if data[i] == 1:
            data[i:i + L + 1] ^= gen_poly

    return ''.join(str(b) for b in data[-L:])


def verify_crc(bit_str, poly_key):
    """返回 (是否通过, 余数)"""
    rem = crc_remainder(bit_str, poly_key)
    return rem == '0' * len(rem), rem


# ============================================================
# 二、文件名解析
# ============================================================
# 格式: 时间(14位)_长度_CRC方式_序号.txt
FILENAME_RE = re.compile(
    r'^(\d{14})_(\d+)_(CRC\d+[AB]?)_(\d+)\.txt$'
)


def parse_filename(name):
    """
    返回 dict 或 None
        { 'timestamp': '20260916154924',
          'length': 5037,
          'crc': 'CRC24',      # 原样保留 CRC6/CRC11/CRC16/CRC24
          'index': 0 }
    """
    m = FILENAME_RE.match(name)
    if not m:
        return None
    return {
        'timestamp': m.group(1),
        'length': int(m.group(2)),
        'crc': m.group(3),
        'index': int(m.group(4)),
    }


# ============================================================
# 三、校验逻辑
# ============================================================
def read_bit_file(path):
    """读取 01 文件，返回纯字符串"""
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()
    return "".join(ch for ch in raw if ch in ('0', '1'))


def verify_one_file(path, info):
    """
    对 CRC-6 / CRC-11 / CRC-16 以及单个 CRC-24A 文件进行整体校验。
    返回 (ok, msg)
    """
    bits = read_bit_file(path)
    crc_tag = info['crc']            # 'CRC6' / 'CRC11' / 'CRC16' / 'CRC24'
    key = crc_tag.replace('CRC', '') # '6' / '11' / '16' / '24'

    if key == '24':
        key = '24A'                  # 单文件 CRC-24 用 24A

    if key not in POLY_DEFS:
        return False, f"未知 CRC 类型: {crc_tag}"

    ok, rem = verify_crc(bits, key)
    if ok:
        return True, (f"✔ 校验通过  [{os.path.basename(path)}]  "
                      f"长度={len(bits)} bit, CRC={crc_tag}")
    else:
        return False, (f"✘ 校验失败  [{os.path.basename(path)}]  "
                       f"长度={len(bits)} bit, CRC={crc_tag}\n"
                       f"    余数 = {rem}")


def verify_group(files, infos):
    """
    CRC-24 多文件包组校验：
      ① 每块独立 CRC-24B 校验
      ② 拼接后整体 CRC-24A 校验（拼接时去掉每块尾部的 24 bit CRC-24B）
    返回 (ok, lines)
    """
    lines = []
    all_ok = True

    # 按 index 排序
    paired = sorted(zip(infos, files), key=lambda x: x[0]['index'])

    payload_parts = []
    for info, path in paired:
        bits = read_bit_file(path)
        ok, rem = verify_crc(bits, '24B')
        if ok:
            lines.append(f"  ✔ 块{info['index']} CRC-24B 校验通过  "
                         f"[{os.path.basename(path)}]  长度={len(bits)}")
        else:
            lines.append(f"  ✘ 块{info['index']} CRC-24B 校验失败  "
                         f"[{os.path.basename(path)}]\n"
                         f"      余数 = {rem}")
            all_ok = False

        # 拼接到一起的应该是去掉 CRC-24B 的载荷部分
        payload_parts.append(bits[:-24])

    # 拼接后整体 CRC-24A 校验
    combined = ''.join(payload_parts)
    if combined:
        ok2, rem2 = verify_crc(combined, '24A')
        if ok2:
            lines.append(f"  ✔ 拼接后整体 CRC-24A 校验通过  "
                         f"总长={len(combined)} bit")
        else:
            lines.append(f"  ✘ 拼接后整体 CRC-24A 校验失败\n"
                         f"      余数 = {rem2}")
            all_ok = False

    return all_ok, lines


# ============================================================
# 四、可视化界面
# ============================================================
class CRCDecoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CRC 校验解码器（3GPP TS 38.212）")
        self.root.geometry("820x920")
        self.root.minsize(720, 700)
        self.root.resizable(True, True)

        self.file_paths = []      # 选中的文件完整路径列表

        self._build_ui()

    # --------------------------------------------------------
    def _build_ui(self):
        # ===== 底部按钮栏 =====
        f_bottom = tk.Frame(self.root)
        f_bottom.pack(side="bottom", fill="x", padx=12, pady=(6, 12))

        self.btn_check = tk.Button(f_bottom, text="开始校验",
                                   width=16, height=2, state="disabled",
                                   command=self.run_check)
        self.btn_check.pack(side="left")

        self.btn_clear = tk.Button(f_bottom, text="清空",
                                   width=10, height=2,
                                   command=self.clear_all)
        self.btn_clear.pack(side="left", padx=8)

        tk.Button(f_bottom, text="退出", width=10, height=2,
                  command=self.root.destroy).pack(side="right")

        # ===== ① 选择文件 =====
        f1 = tk.LabelFrame(self.root,
                           text="① 选择待校验文件（可多选）",
                           padx=10, pady=8)
        f1.pack(side="top", fill="x", padx=12, pady=6)

        tk.Button(f1, text="选择文件…", width=14,
                  command=self.select_files).pack(side="left")

        self.lbl_files = tk.Label(f1, text="尚未选择文件",
                                  anchor="w", fg="gray")
        self.lbl_files.pack(side="left", padx=10, fill="x", expand=True)

        # ===== ② 文件列表 =====
        f2 = tk.LabelFrame(self.root, text="② 已选文件列表",
                           padx=10, pady=8)
        f2.pack(side="top", fill="both", expand=False, padx=12, pady=6)

        self.txt_files = tk.Text(f2, height=8, wrap="none",
                                 font=("Consolas", 9))
        self.txt_files.pack(fill="both", expand=True)
        self.txt_files.config(state="disabled")

        # ===== ③ 提示信息 =====
        f3 = tk.LabelFrame(self.root, text="③ 提示信息",
                           padx=10, pady=8)
        f3.pack(side="top", fill="x", padx=12, pady=6)
        self.lbl_hint = tk.Label(f3, text="点击『选择文件…』加载 .txt",
                                 anchor="w", justify="left", fg="gray",
                                 font=("Microsoft YaHei", 10))
        self.lbl_hint.pack(fill="x")

        # ===== ④ 校验结果 =====
        f4 = tk.LabelFrame(self.root, text="④ 校验结果",
                           padx=10, pady=8)
        f4.pack(side="top", fill="both", expand=True, padx=12, pady=6)

        self.txt_result = tk.Text(f4, wrap="word",
                                  font=("Consolas", 10))
        self.txt_result.pack(fill="both", expand=True)
        self.txt_result.config(state="disabled")

        # 文字标签（用于着色）
        self.txt_result.tag_config("ok",   foreground="green")
        self.txt_result.tag_config("fail", foreground="red")
        self.txt_result.tag_config("hdr",  foreground="blue",
                                   font=("Consolas", 10, "bold"))

    # --------------------------------------------------------
    def set_text(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def append_result(self, text, tag=None):
        self.txt_result.config(state="normal")
        if tag:
            self.txt_result.insert("end", text + "\n", tag)
        else:
            self.txt_result.insert("end", text + "\n")
        self.txt_result.see("end")
        self.txt_result.config(state="disabled")

    # --------------------------------------------------------
    def select_files(self):
        paths = filedialog.askopenfilenames(
            title="请选择要校验的 .txt 文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if not paths:
            return

        self.file_paths = list(paths)

        # 显示列表
        names = [os.path.basename(p) for p in self.file_paths]
        self.set_text(self.txt_files, "\n".join(names))
        self.lbl_files.config(text=f"已选 {len(names)} 个文件", fg="black")

        # 初步解析 & 显示分组提示
        parsed = self.analyze_files()
        hint_lines = [f"共 {len(self.file_paths)} 个文件"]
        for crc_tag, groups in parsed.items():
            hint_lines.append(f"  CRC 类型 {crc_tag}: "
                              f"{sum(len(g) for g in groups.values())} 个文件, "
                              f"{len(groups)} 个包组")
        self.lbl_hint.config(text="\n".join(hint_lines), fg="black")

        self.btn_check.config(state="normal")
        self.set_text(self.txt_result, "")

    # --------------------------------------------------------
    def clear_all(self):
        self.file_paths = []
        self.set_text(self.txt_files, "")
        self.set_text(self.txt_result, "")
        self.lbl_files.config(text="尚未选择文件", fg="gray")
        self.lbl_hint.config(text="点击『选择文件…』加载 .txt", fg="gray")
        self.btn_check.config(state="disabled")

    # --------------------------------------------------------
    def analyze_files(self):
        """
        解析所有文件，按 CRC 类型分组，CRC-24 再按时间戳分子组。
        返回: { 'CRC6':  {ts: [(info,path), ...]},
                'CRC16': {...},
                'CRC24': {ts: [...]}, ... }
        """
        result = defaultdict(lambda: defaultdict(list))
        for p in self.file_paths:
            name = os.path.basename(p)
            info = parse_filename(name)
            if info is None:
                # 无法识别，放到特殊组
                result['UNKNOWN'][('_', name)].append(
                    ({'timestamp': '_', 'length': 0,
                      'crc': 'UNKNOWN', 'index': 0}, p)
                )
                continue
            result[info['crc']][info['timestamp']].append((info, p))
        return result

    # --------------------------------------------------------
    def run_check(self):
        if not self.file_paths:
            return

        self.set_text(self.txt_result, "")
        parsed = self.analyze_files()
        overall_ok = True
        total_checked = 0

        # ---- 依次处理每种 CRC 类型 ----
        for crc_tag in sorted(parsed.keys()):
            self.append_result(f"===== CRC 类型: {crc_tag} =====", "hdr")

            groups = parsed[crc_tag]      # {timestamp: [(info,path), ...]}

            for ts, items in sorted(groups.items()):
                items = sorted(items, key=lambda x: x[0]['index'])
                n_files = len(items)

                if crc_tag == 'CRC24':
                    # CRC-24 特殊：按包组处理
                    if n_files == 1:
                        info, path = items[0]
                        self.append_result(
                            f"[包组 {ts}] 单文件 → CRC-24A 校验"
                        )
                        ok, msg = verify_one_file(path, info)
                        total_checked += 1
                        self.append_result("  " + msg,
                                           "ok" if ok else "fail")
                        overall_ok &= ok
                    else:
                        self.append_result(
                            f"[包组 {ts}] 多文件({n_files}块) → "
                            f"逐块 CRC-24B + 拼接 CRC-24A"
                        )
                        files = [p for _, p in items]
                        infos = [i for i, _ in items]
                        ok, lines = verify_group(files, infos)
                        total_checked += n_files
                        for line in lines:
                            tag = None
                            if "✔" in line:
                                tag = "ok"
                            elif "✘" in line:
                                tag = "fail"
                            self.append_result(line, tag)
                        overall_ok &= ok

                else:
                    # CRC-6 / CRC-11 / CRC-16：逐文件处理
                    for info, path in items:
                        ok, msg = verify_one_file(path, info)
                        total_checked += 1
                        self.append_result("  " + msg,
                                           "ok" if ok else "fail")
                        overall_ok &= ok

            self.append_result("")

        # ---- 总结 ----
        if overall_ok:
            self.append_result(
                f"全部通过 ✔  （共校验 {total_checked} 个文件）", "ok"
            )
        else:
            self.append_result(
                f"存在校验失败 ✘  （共校验 {total_checked} 个文件）", "fail"
            )


# ============================================================
# 主入口
# ============================================================
def main():
    root = tk.Tk()
    CRCDecoderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()