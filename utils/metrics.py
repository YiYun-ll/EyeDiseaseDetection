import numpy as np
from sklearn.metrics import  precision_score, recall_score, f1_score, accuracy_score
from sklearn.metrics import  confusion_matrix
import torch

def calculate_metrics(y_true, y_pred, threshold=0.5,return_class_metrics=True):
    # 确保输入为浮点张量
    y_true = y_true.float()
    
    # 对logits应用sigmoid
    y_proba = torch.sigmoid(y_pred)
    y_pred_binary = (y_proba > threshold).float()
    
    # 转换为numpy数组以使用sklearn的指标函数
    y_true_np = y_true.cpu().numpy()
    y_pred_binary_np = y_pred_binary.cpu().numpy()
    
    # 计算每个样本的精确匹配率
    exact_match = (y_pred_binary == y_true).all(dim=1).float().mean().item()
    # 计算准确率（每个标签的正确率平均值）
    accuracy = ((y_pred_binary == y_true).float().mean()).item()
    # 使用sklearn计算微平均指标
    precision = precision_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)
    recall = recall_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)
    f1 = f1_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)

    # 计算每个类别的指标
    class_metrics = {}
    for i in range(y_true.shape[1]):
        class_precision = precision_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
        class_recall = recall_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
        class_f1 = f1_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
        class_accuracy = accuracy_score(y_true_np[:, i], y_pred_binary_np[:, i])
        # 计算混淆矩阵
        tn, fp, fn, tp = confusion_matrix(y_true_np[:, i], y_pred_binary_np[:, i], labels=[0, 1]).ravel()
        
        # 计算特异性 (真阴性率)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        # 计算阳性预测值和阴性预测值
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0  # 精确率
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        
        # 计算类别分布
        pos_ratio = np.mean(y_true_np[:, i])
        pred_pos_ratio = np.mean(y_pred_binary_np[:, i])
        class_metrics[f'class_{i}'] = {
            'accuracy': class_accuracy,
            'precision': class_precision,
            'recall': class_recall,
            'f1': class_f1,
            'specificity': specificity,
            'ppv': ppv,
            'npv': npv,
            'tp': tp,
            'fp': fp,
            'tn': tn,
            'fn': fn,
            'pos_ratio': pos_ratio,
            'pred_pos_ratio': pred_pos_ratio
        }
    
    return {
        "exact_match": exact_match,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "class_metrics": class_metrics if return_class_metrics else None
    }

def calculate_metrics_with_thresholds(y_true, y_pred, thresholds, return_class_metrics=True):
    y_true = y_true.float()
    y_proba = torch.sigmoid(y_pred)
    
    # 应用类别特定阈值
    y_pred_binary = torch.zeros_like(y_proba)
    for i, threshold in enumerate(thresholds):
        safe_threshold = max(min(threshold,0.95),0.05)
        y_pred_binary[:, i] = (y_proba[:, i] > safe_threshold).float()
    
    # 转换为numpy数组
    y_true_np = y_true.numpy()
    y_pred_binary_np = y_pred_binary.numpy()
    
    # 计算每个样本的精确匹配率
    exact_match = (y_pred_binary == y_true).all(dim=1).float().mean().item()
    
    # 计算准确率（每个标签的正确率平均值）
    accuracy = ((y_pred_binary == y_true).float().mean()).item()
    
    # 使用sklearn计算微平均指标
    precision = precision_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)
    recall = recall_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)
    f1 = f1_score(y_true_np, y_pred_binary_np, average='micro', zero_division=0)

    
    # 计算每个类别的详细指标
    class_metrics = {}
    if return_class_metrics:
        for i in range(y_true.shape[1]):
            # 计算基本指标
            class_precision = precision_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
            class_recall = recall_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
            class_f1 = f1_score(y_true_np[:, i], y_pred_binary_np[:, i], zero_division=0)
            class_accuracy = accuracy_score(y_true_np[:, i], y_pred_binary_np[:, i])
            
            # 计算混淆矩阵
            tn, fp, fn, tp = confusion_matrix(y_true_np[:, i], y_pred_binary_np[:, i], labels=[0, 1]).ravel()
            
            # 计算特异性 (真阴性率)
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
            
            # 计算阳性预测值和阴性预测值
            ppv = tp / (tp + fp) if (tp + fp) > 0 else 0  # 精确率
            npv = tn / (tn + fn) if (tn + fn) > 0 else 0
            
            # 计算类别分布
            pos_ratio = np.mean(y_true_np[:, i])
            pred_pos_ratio = np.mean(y_pred_binary_np[:, i])
            
            class_metrics[f'class_{i}'] = {
                'threshold': thresholds[i],
                'accuracy': class_accuracy,
                'precision': class_precision,
                'recall': class_recall,
                'f1': class_f1,
                'specificity': specificity,
                'ppv': ppv,
                'npv': npv,
                'tp': tp,
                'fp': fp,
                'tn': tn,
                'fn': fn,
                'pos_ratio': pos_ratio,
                'pred_pos_ratio': pred_pos_ratio
            }

    return {
        "exact_match": exact_match,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "class_metrics": class_metrics if return_class_metrics else None,
        "thresholds": thresholds.tolist() if isinstance(thresholds, torch.Tensor) else thresholds
    }

# 测试用例
if __name__ == "__main__":
    # 创建测试数据
    y_true = torch.tensor([[1, 0, 0], [0, 1, 1], [1, 1, 0]], dtype=torch.float)
    # 创建logits (未经过sigmoid的原始输出)
    y_pred = torch.tensor([[2.0, -2.0, -1.0], [-1.0, 1.5, 0.5], [1.2, 0.9, -0.5]], dtype=torch.float)
    
    # 计算指标
    metrics = calculate_metrics(y_true, y_pred)
    print("整体指标:")
    for k, v in metrics.items():
        if k != 'class_metrics':
            print(f"{k}: {v:.4f}")
    
    print("\n各类别指标:")
    for class_name, class_metric in metrics['class_metrics'].items():
        print(f"{class_name}:")
        for metric_name, value in class_metric.items():
            print(f"  {metric_name}: {value:.4f}")