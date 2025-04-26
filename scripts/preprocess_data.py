
import csv
import os
import pandas as pd
import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit
from collections import Counter

# 定义目录结构
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
SPLIT_DIR = os.path.join(DATA_DIR, 'processed')

# 类别定义
CLASS_NAMES = ['normal', 'diabetes', 'glaucoma', 'cataract', 
              'amd', 'hypertension', 'myopia', 'other']
NUM_CLASSES = len(CLASS_NAMES)

def load_data():
    input_csv = os.path.join(DATA_DIR, 'category.csv')
    
    data = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        next(f)  # 跳过首行标题
        
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            # 分割路径和标签
            parts = line.split(',', 1)
            path = parts[0].strip()
            
            # 处理多标签
            multilabel = [0] * NUM_CLASSES
            if len(parts) > 1:
                for lbl in parts[1].split(','):
                    lbl = lbl.strip().lower()
                    try:
                        idx = CLASS_NAMES.index(lbl)
                        multilabel[idx] = 1
                    except ValueError:
                        print(f"警告：第{line_num}行发现未知标签 '{lbl}'")
            
            if sum(multilabel) == 0:
                print(f"警告：第{line_num}行没有标签")
                multilabel[CLASS_NAMES.index('other')] = 1

            data.append({
                'image_path': path.strip(),  # 保留原始路径结构
                'labels': multilabel  # 直接保存列表格式
            })
    
    return pd.DataFrame(data)

def analyze_label_distribution(df):
    y = np.array(df['labels'].tolist())
    
    # 计算每个类别的样本数
    class_counts = []
    for i in range(NUM_CLASSES):
        class_counts.append(y[:, i].sum())
    
    # 计算每个样本的标签数量分布
    label_counts_per_sample = [sum(labels) for labels in y]
    label_count_distribution = Counter(label_counts_per_sample)
    
    print("\n标签分布分析:")
    print(f"样本总数: {len(df)}")
    print("每个类别的样本数:")
    for i, class_name in enumerate(CLASS_NAMES):
        print(f"  {class_name}: {class_counts[i]} ({class_counts[i]/len(df):.1%})")
    
    print("\n每个样本的标签数量分布:")
    for count, freq in sorted(label_count_distribution.items()):
        print(f"  {count}个标签: {freq}个样本 ({freq/len(df):.1%})")
    
    # 检查极度不平衡的类别
    min_class_count = min(class_counts)
    min_class_idx = class_counts.index(min_class_count)
    if min_class_count < 10:
        print(f"\n警告: '{CLASS_NAMES[min_class_idx]}'类别样本数量极少({min_class_count})，可能影响模型训练")
    
    return class_counts, label_count_distribution

def stratified_split_old(df, ratios=(0.9, 0.1, 0.0),random_state=42):
    X = df.index.values
    y = np.array(df['labels'].tolist())

    print("\n原始数据集标签分布:")
    class_counts, _ = analyze_label_distribution(df)
    
    if ratios[2] > 0:
        # 第一次划分：train+val vs test
        msss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=ratios[2], random_state=random_state)
        train_val_idx, test_idx = next(msss.split(X, y))
    
        # 第二次划分：train vs val
        val_ratio = ratios[1] / (ratios[0] + ratios[1])
        msss_val = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=val_ratio, random_state=42)
        train_idx, val_idx = next(msss_val.split(X[train_val_idx], y[train_val_idx]))

        # 创建数据集
        train_df = df.iloc[train_val_idx[train_idx]]
        val_df = df.iloc[train_val_idx[val_idx]]
        test_df = df.iloc[test_idx]
    else:
        # 直接划分训练集和验证集
        msss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=ratios[1], random_state=random_state)
        train_idx, val_idx = next(msss.split(X, y))
        
        # 创建数据集
        train_df = df.iloc[train_idx]
        val_df = df.iloc[val_idx]
        test_df = pd.DataFrame(columns=df.columns)  # 创建空的测试集DataFrame
    
     # 验证划分结果
    print("\n划分后各数据集标签分布:")
    print("训练集:")
    train_class_counts, _ = analyze_label_distribution(train_df)
    print("验证集:")
    val_class_counts, _ = analyze_label_distribution(val_df)
    print("验证集:")
    test_class_counts, _ = analyze_label_distribution(test_df)
    
    if ratios[2] > 0:
        print("测试集:")
        test_class_counts, _ = analyze_label_distribution(test_df)
    
    # 检查划分是否合理
    for i, class_name in enumerate(CLASS_NAMES):
        if len(train_df) > 0:
            train_ratio = train_class_counts[i] / class_counts[i]
            print(f"\n{class_name}类别划分比例: 训练集={train_ratio:.2f}", end="")
        
        if len(val_df) > 0:
            val_ratio = val_class_counts[i] / class_counts[i]
            print(f", 验证集={val_ratio:.2f}", end="")
        
        if ratios[2] > 0 and len(test_df) > 0:
            test_ratio = test_class_counts[i] / class_counts[i]
            print(f", 测试集={test_ratio:.2f}", end="")
        
        print()
    return train_df, val_df, test_df

def stratified_split(df, ratios=(0.8, 0.2, 0.0), random_state=42):
    X = df.index.values
    y = np.array(df['labels'].tolist())
    
    # 分析原始数据标签分布
    print("\n原始数据集标签分布:")
    class_counts, _ = analyze_label_distribution(df)
    
    if ratios[2] > 0:
        # 第一次划分：train+val vs test
        msss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=ratios[2], random_state=random_state)
        train_val_idx, test_idx = next(msss.split(X, y))
    
        # 第二次划分：train vs val
        val_ratio = ratios[1] / (ratios[0] + ratios[1])
        msss_val = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=val_ratio, random_state=random_state)
        train_idx, val_idx = next(msss_val.split(X[train_val_idx], y[train_val_idx]))
    
        train_df = df.iloc[train_val_idx[train_idx]]
        val_df = df.iloc[train_val_idx[val_idx]]
        test_df = df.iloc[test_idx]
    else:
        # 直接划分训练集和验证集
        msss = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=ratios[1], random_state=42)
        train_idx, val_idx = next(msss.split(X, y))
        
        # 创建数据集
        train_df = df.iloc[train_idx]
        val_df = df.iloc[val_idx]
        test_df = pd.DataFrame(columns=df.columns)
    
    # 验证划分结果
    print("\n划分后各数据集标签分布:")
    print("训练集:")
    train_class_counts, _ = analyze_label_distribution(train_df)
    print("验证集:")
    val_class_counts, _ = analyze_label_distribution(val_df)
    if ratios[2] > 0:
        print("测试集:")
        test_class_counts, _ = analyze_label_distribution(test_df)
    
    # 检查划分是否合理
    for i, class_name in enumerate(CLASS_NAMES):
        if len(train_df) > 0:
            train_ratio = train_class_counts[i] / class_counts[i]
            print(f"\n{class_name}类别划分比例: 训练集={train_ratio:.2f}", end="")
        
        if len(val_df) > 0:
            val_ratio = val_class_counts[i] / class_counts[i]
            print(f", 验证集={val_ratio:.2f}", end="")
        
        if ratios[2] > 0 and len(test_df) > 0:
            test_ratio = test_class_counts[i] / class_counts[i]
            print(f", 测试集={test_ratio:.2f}", end="")
        
        print()
    
    return train_df, val_df, test_df

def save_datasets(train_df, val_df, test_df):
    os.makedirs(SPLIT_DIR, exist_ok=True)
    
    output_files = {
        'train.csv': train_df,
        'val.csv': val_df,
    }
    if len(test_df) > 0:
        output_files['test.csv'] = test_df

    for filename, df in output_files.items():
        output_path = os.path.join(SPLIT_DIR, filename)
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            # 关键修改：强制所有字段加引号
            writer = csv.writer(f, 
                              quoting=csv.QUOTE_ALL,  # 强制所有字段加引号
                              delimiter=',')
            
            # 写入带引号的标题行
            writer.writerow(['image_path', 'labels'])
            
            for _, row in df.iterrows():
                # 路径处理
                clean_path = row['image_path']
                # 标签处理（去除空格）
                labels_str = f"[{','.join(map(str, row['labels']))}]"  
                
                writer.writerow([clean_path, labels_str])

    # 验证保存的数据集
    for filename, df in output_files.items():
        output_path = os.path.join(SPLIT_DIR, filename)
        print(f"\n验证保存的数据集: {filename}")
        
        # 尝试重新加载CSV以验证格式
        try:
            test_df = pd.read_csv(output_path)
            print(f"  成功加载 {len(test_df)} 行")
            
            # 验证标签格式
            sample_label = test_df['labels'].iloc[0]
            print(f"  样本标签格式: {sample_label}")
            
            # 验证是否可以解析标签
            import ast
            try:
                parsed_label = ast.literal_eval(sample_label)
                print(f"  解析后的标签: {parsed_label}")
            except:
                print("  警告: 无法解析标签字符串，可能影响后续数据加载")
                
        except Exception as e:
            print(f"  警告: 无法验证保存的数据集: {str(e)}")

def print_statistics(df, name):
    y = np.array(df['labels'].tolist())
    print(f"\n{name} 集 ({len(df)} 样本)")
    print("类别分布:")
    for i, class_name in enumerate(CLASS_NAMES):
        count = y[:, i].sum()
        print(f"{class_name}: {count} ({count/len(df):.1%})")

def main():
    # 加载数据
    df = load_data()
    
    # 数据验证
    if len(df) == 0:
        raise ValueError("原始数据集为空，请检查category.csv文件")
    
    print("="*50)
    print("原始数据集分析")
    analyze_label_distribution(df)

    # 划分数据集
    train_df, val_df, test_df = stratified_split(df,ratios=(0.92,0.08,0.0))
    
    # 保存数据集
    save_datasets(train_df, val_df, test_df)
    
    # 打印统计
    print("="*50)
    print_statistics(df, "原始数据")
    print_statistics(train_df, "训练")
    print_statistics(val_df, "验证")
    print_statistics(test_df, "测试")
    print("="*50)

if __name__ == "__main__":
    main()