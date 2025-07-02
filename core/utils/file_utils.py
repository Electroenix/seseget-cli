import os
import re


def make_filename_valid(path):
    """使文件名合法化,不能对路径名使用,会把'\\'去掉"""
    path = path.replace('/', '')
    path = path.replace('\\', '')
    path = path.replace(':', '')
    path = path.replace('*', '')
    path = path.replace('?', '')
    path = path.replace('<', '')
    path = path.replace('>', '')
    path = path.replace('"', '')
    path = path.replace('|', '')
    path = path.rstrip()
    path = path.rstrip('.')

    return path


# 命名不重复的目录名
def make_diff_dir_name(dir):
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
    return os.path.basename(os.path.normpath(path))

