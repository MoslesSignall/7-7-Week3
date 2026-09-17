import os
import numpy as np


POLY_DEFS = {
    '6':   np.array([1, 1, 0, 0, 0, 0, 1], dtype=np.uint8),
    '11':  np.array([1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1], dtype=np.uint8),
    '16':  np.array([1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], dtype=np.uint8),
    '24A': np.array([1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1], dtype=np.uint8),
    '24B': np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1], dtype=np.uint8),
    '24C': np.array([1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1], dtype=np.uint8),
}

def txt_read(pace):
    """
    功能：读取txt文件内容，其中txt内部全为0/1序列
    输入值：
        pace：文件路径
    返回值：
        bits：文件比特数
        str_ori：文件中的信息
    """
    with open(pace, 'r', encoding='utf-8') as f:
        str_ori = f.read().strip()
    bits=len(str_ori)

    return bits, str_ori

def _crc_encode(str_ori, poly_str):
    """
    功能：通用CRC编码函数
    输入值:
        str_ori: 只含0/1的字符串，或者由0/1组成的序列
        poly_str: 多项式类型字符串('6','11','16','24A','24B','24C')
    返回值:
        str_crc: 进行了CRC操作后的比特序列
    """
    gen_poly = POLY_DEFS[poly_str]
    L = len(gen_poly) - 1  # CRC 长度

    # 将输入统一成 0/1 的 numpy 数组
    if isinstance(str_ori, str):
        data = np.array([int(c) for c in str_ori.strip()], dtype=np.uint8)
    else:
        data = np.asarray(str_ori, dtype=np.uint8).flatten()
        data = (data != 0).astype(np.uint8)

    M = len(data)

    # 在数据后补 L 个 0
    padded = np.concatenate([data, np.zeros(L, dtype=np.uint8)])

    # 模 2 除法
    for i in range(M):
        if padded[i] == 1:
            padded[i:i + L + 1] ^= gen_poly

    # 余数即最后 L 位 CRC
    crc_bits = padded[-L:]

    # 拼接：原始数据 + CRC
    str_crc = np.concatenate([data, crc_bits])

    # 转回字符串
    return ''.join(str(int(b)) for b in str_crc)


def CRC_6(str_ori):
    """CRC-6 (gCRC6)，输出：原始比特 + 6 位 CRC"""
    return _crc_encode(str_ori, '6')


def CRC_11(str_ori):
    """CRC-11 (gCRC11)，输出：原始比特 + 11 位 CRC"""
    return _crc_encode(str_ori, '11')


def CRC_16(str_ori):
    """CRC-16 (gCRC16)，输出：原始比特 + 16 位 CRC"""
    return _crc_encode(str_ori, '16')


def CRC_24A(str_ori):
    """CRC-24A (gCRC24A)，输出：原始比特 + 24 位 CRC"""
    return _crc_encode(str_ori, '24A')


def CRC_24B(str_ori):
    """CRC-24B (gCRC24B)，输出：原始比特 + 24 位 CRC"""
    return _crc_encode(str_ori, '24B')

def CRC_24C(str_ori):
    """CRC-24C (gCRC24C)，输出：原始比特 + 24 位 CRC"""
    return _crc_encode(str_ori, '24C')

def CRC_judge(bits,str_ori):
    """
    功能：根据比特数选择CRC类型
    输入值：
        bits：比特数
        str_ori：原始比特序列
    返回值：
        str_crc：进行CRC操作后的比特序列
    """
    if bits <= 19:
        return CRC_6(str_ori)
    elif bits <= 39:
        return CRC_11(str_ori)
    elif bits <= 3824:
        return CRC_16(str_ori)
    else:
        return CRC_24A(str_ori)

def CRC_24B_judge(bits,str_input):
    """
    功能：根据比特数选择是否进行CRC-24B
    输入值：
        bits：比特数
        str_input：原始比特序列
    返回值：
        str_crc：进行CRC操作后的比特序列
    """
    if bits <= 8424:
        return str_input  # 不进行CRC-24B
    else:
        # 先分块
        bits=bits+24
        n=(bits+8423)//8424
        last=bits%n
        lengths=[bits//n+1]*last+[bits//n]*(n-last)

        str_crc=[] # 存储分块之后的比特流
        pos = 0
        for L in lengths:
            str_crc.append(str_input[pos:pos+L])
            pos += L
        print([len(p) for p in str_crc])

        # 再补零
        for i in range(last+1, n+1):
            str_crc[i-1]=str_crc[i-1]+'0'

        # 最后对每一个分块做CRC-24B
        for i in range(n):
            str_crc[i]=CRC_24B(str_crc[i])

        return str_crc

# 计算字符串（组）的行数
def count_lines(x):
    lines = [x] if isinstance(x, str) else list(x)
    return len(lines)

def crc_decoder_root(bits,str_crc):
    """
    功能：CRC解码函数
    输入值：
        bits：比特数
        str_crc：进行CRC操作后的比特序列（字符串或列表）
    返回值：
        str_decoded：解码后的比特序列
    """
    if bits <= 19:
        return crc_6_decoder(str_crc)
    elif bits <= 39:
        return crc_11_decoder(str_crc)
    elif bits <= 3824:
        return crc_16_decoder(str_crc)
    elif bits <= 8424:
        return crc_24a_decoder(str_crc)
    else:
        bits=bits+24
        n=(bits+8423)//8424
        last=bits%n
        str_decrc_24b_1=""
        flag=0
        for i in range(n):
            # 对每一个分块做CRC-24B解码
            str_nowline=str_crc[i]
            str_decrc_1=crc_24b_decoder(str_nowline)
            if str_decrc_1[0]==False:
                print("CRC-24B校验错误,请检查数据")
                return None

            # 去零
            if i>last-1:
                str_decrc_2=str_nowline[:-25]
            else:
                str_decrc_2=str_nowline[:-24]
            str_decrc_24b_1=str_decrc_24b_1+str_decrc_2
            if str_decrc_1[0]==True:
                flag=flag+1
        
        if flag==n:
            print("CRC-24B校验全部正确,下面进行CRC-24A校验")
        str_decrc=crc_24a_decoder(str_decrc_24b_1)
        return str_decrc

def _crc_decode(str_crc, poly_str):
    """
    功能：通用CRC校验函数
    输入值:
        str_crc: 接收到的完整码字（原始数据 + CRC），只含0/1的字符串
        poly_str: 多项式类型字符串('6','11','16','24A','24B','24C')
    返回值:
        is_valid: bool，True表示校验通过（余数为0），False表示有误
        remainder: 余数（0/1字符串），便于调试查看
    """
    gen_poly = POLY_DEFS[poly_str]
    L = len(gen_poly) - 1  # CRC 长度
    N = len(str_crc)

    # 长度必须大于CRC长度，否则无法校验
    if N <= L:
        return False, '数据长度不足'

    # 复制一份，用于模2除法
    work = list(str_crc)

    # 模2除法：对完整码字做除法
    for i in range(N - L):
        if work[i] == '1':
            for j in range(L + 1):
                work[i + j] = str(int(work[i + j]) ^ int(gen_poly[j]))

    # 余数即最后 L 位
    remainder = work[-L:]
    is_valid = np.any(remainder)  # 余数全0则正确
    print(f"CRC-{poly_str} 校验结果: {'正确' if is_valid else '错误'}, 余数: {''.join(remainder)}")

    return str_crc[:-L]

def crc_6_decoder(str_crc):
    """CRC-6 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '6')


def crc_11_decoder(str_crc):
    """CRC-11 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '11')


def crc_16_decoder(str_crc):
    """CRC-16 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '16')


def crc_24a_decoder(str_crc):
    """CRC-24A 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '24A')


def crc_24b_decoder(str_crc):
    """CRC-24B 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '24B')


def crc_24c_decoder(str_crc):
    """CRC-24C 解码校验，返回 (是否正确, 余数)"""
    return _crc_decode(str_crc, '24C')


# ==================== 新增封装模块 ====================

def crc_add_check(file_path):
    """
    CRC 加校验模块

    输入：
        file_path：只含0/1序列的txt文件路径

    返回：
        str_crc：加校验后的完整比特串（字符串）。
                 若使用CRC-24B分块，则各分块以列表形式返回，
                 但为保持统一接口，此处将其拼接为一个字符串返回。
        bits：原始文件比特数
    """
    # 1. 读取文件
    bits, str_ori = txt_read(file_path)

    # 2. 第一层 CRC 编码（根据 bits 选择 CRC-6/11/16/24A）
    str_crc = CRC_judge(bits, str_ori)

    # 3. 判断是否进行 CRC-24B 分块
    str_crc = CRC_24B_judge(bits, str_crc)

    # 4. 统一返回格式
    if isinstance(str_crc, list):
        # 分块情况：拼接为一个字符串返回（各块之间无分隔符）
        # 同时也可以保留列表信息，但接口要求返回 string 变量
        str_crc_str = ''.join(str_crc)
    else:
        str_crc_str = str_crc

    return str_crc_str, bits


def crc_remove_check(str_crc, bits):
    """
    CRC 解校验模块
    输入：
        str_crc：加校验后的完整比特串（字符串）。
                 若原始编码时使用了CRC-24B分块，需要按分块规则重新拆分。
        bits：原始文件比特数
    返回：
        is_valid：bool，True 表示校验通过，False 表示校验失败
        str_decoded：解码后的原始比特串（字符串）；校验失败时返回 None
    """
    # 判断是否使用了 CRC-24B 分块（与编码端逻辑一致）
    use_24b = bits > 8424

    if not use_24b:
        # 未分块：直接调用解码函数
        str_decoded = crc_decoder_root(bits, str_crc)
        is_valid = (str_decoded is not None)
        return is_valid, str_decoded
    else:
        # 分块情况：需要先将字符串按分块规则还原成列表
        bits_plus = bits + 24
        n = (bits_plus + 8423) // 8424
        last = bits_plus % n
        lengths = [bits_plus // n + 1] * last + [bits_plus // n] * (n - last)

        # 计算每块在最终码流中的总长度（补零 + CRC-24B）
        block_final_lengths = []
        for i in range(n):
            orig_len = lengths[i]
            padded_len = orig_len + (1 if i >= last else 0)
            final_len = padded_len + 24  # 加 24 位 CRC-24B
            block_final_lengths.append(final_len)

        # 按长度拆分字符串
        str_crc_blocks = []
        pos = 0
        for L in block_final_lengths:
            str_crc_blocks.append(str_crc[pos:pos + L])
            pos += L

        # 调用解码函数（crc_decoder_root 内部会逐块校验 CRC-24B，
        # 然后拼接去零后的数据，再做 CRC-24A 校验）
        str_decoded = crc_decoder_root(bits, str_crc_blocks)
        is_valid = (str_decoded is not None)
        return is_valid, str_decoded


# ==================== 测试入口 ====================
def main():
    # 测试示例
    pace = 'randstr_3820bits.txt'

    # 加校验
    str_crc, bits = crc_add_check(pace)
    print(f"原始比特数 bits = {bits}")
    print(f"加校验后总长度 = {len(str_crc)}")
    print(f"加校验后前 100 位：{str_crc[:100]}")

    # 解校验
    is_valid, str_decoded = crc_remove_check(str_crc, bits)
    print(f"\n校验结果：{'通过' if is_valid else '失败'}")
    print(f"解码结果前 100 位：{str_decoded[:100] if str_decoded else None}")


if __name__ == '__main__':
    main()