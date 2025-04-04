import os
import math


def find_files_with_multilines(folder_path):
    """查找包含多行内容的txt文件"""
    multiline_files = []

    for filename in os.listdir(folder_path):
        if not filename.endswith('.txt'):
            continue

        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r') as file:
            lines = [line.strip() for line in file if line.strip()]

            if len(lines) > 1:
                multiline_files.append(filename)

    return multiline_files


def calculate_diameter(w_norm, h_norm):
    """计算归一化宽高的直径（使用对角线长度）"""
    return max(w_norm*150, h_norm*150)


def find_files_by_diameter(folder_path, min_d, max_d):
    """根据直径范围查找文件"""
    matched_files = []

    for filename in os.listdir(folder_path):
        if not filename.endswith('.txt'):
            continue

        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                try:
                    # 解析每行的五个数字
                    _, _, _, w_norm, h_norm = map(float, line.split())
                    diameter = calculate_diameter(w_norm, h_norm)

                    if min_d <= diameter <= max_d:
                        matched_files.append(filename)
                        break  # 找到匹配即记录，跳出当前文件循环
                except:
                    continue  # 忽略格式错误行

    return matched_files


if __name__ == "__main__":
    # 输入文件夹路径
    folder = input("请输入要扫描的文件夹路径：").strip()

    # 功能1：查找多行文件
    print("\n正在扫描包含多行内容的文件...")
    multiline_files = find_files_with_multilines(folder)
    print(f"找到 {len(multiline_files)} 个多行文件：")
    print('\n'.join(multiline_files) or "无结果")

    # 功能2：按直径范围查找文件
    print("\n正在按直径范围扫描文件...")
    try:
        min_d = float(input("请输入最小直径："))
        max_d = float(input("请输入最大直径："))
        diameter_files = find_files_by_diameter(folder, min_d, max_d)

        print(f"找到 {len(diameter_files)} 个符合直径范围的文件：")
        print('\n'.join(diameter_files) or "无结果")
    except ValueError:
        print("错误：请输入有效的数字范围")
