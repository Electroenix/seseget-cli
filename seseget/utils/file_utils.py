import os
import re


def make_filename_valid(filename):
    """使文件名合法化,不能对路径名使用,会把'\\'去掉"""
    replace = " "
    filename = re.sub(r'[\x00-\x1f\x7f]', replace, filename)
    filename = re.sub(r'[\\/*?:<">|]', replace, filename)
    filename = re.sub(r'\s+', replace, filename)
    filename = filename.strip()
    filename = filename.rstrip('.')

    return filename


def make_diff_dir_name(dir):
    """命名不重复的目录名"""
    if os.path.exists(dir):
        regex_file_index = re.compile(r'(?<=_\[)\d+(?=\]$)')
        result = regex_file_index.search(dir)
        file_index = ''
        if result:
            file_index = result.group()

        # 如果目录没有序号，则目录名加上序号
        if file_index == '':
            dir = dir + '_[1]'
        # 如果目录已存在序号，则序号+1
        else:
            dir = regex_file_index.sub('%d' % (int(file_index) + 1), dir)

        dir = make_diff_dir_name(dir)

    return dir


def get_file_basename(path):
    """获取完整路径中的目标文件名"""
    return os.path.basename(os.path.normpath(path))


def print_to_file(filename: str, content: str | bytes, mode="w"):
    with open(filename, mode) as f:
        f.write(content)
