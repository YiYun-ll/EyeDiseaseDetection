import ast
import os
import torch
from torchvision import transforms
from torch.utils.data import Dataset
from torchvision.io import read_image
import pandas as pd
from PIL import Image
import torchvision.transforms.functional as F
import torchvision

class EyeDataset(Dataset):
    def __init__(self, csv_path, data_root,transform=None):
        self.data = pd.read_csv(csv_path)
        self.data_root = os.path.abspath(data_root)
        self.transform = transform
        
        # 拼接完整图像路径：data_root + image_path
        self.img_paths = [
            os.path.join(self.data_root, img_name)
            for img_name in self.data["image_path"]
        ]
        
        # 解析多标签
        self.labels = self.data["labels"].apply(ast.literal_eval).tolist()
        print(f"示例完整路径: {self.img_paths[0]}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        img_path = self.img_paths[index]
        label = self.labels[index]
        
        try:
            img = Image.open(img_path).convert('RGB')
            # 直接应用transform到PIL图像
            if self.transform:
                img = self.transform(img)
            else:
                # 如果没有transform，至少转换为tensor
                img = F.to_tensor(img)
    
        except Exception as e:
            print(f"加载图像出错 {img_path}: {str(e)}")
            # 创建一个空的tensor作为替代
            img = torch.zeros((3,380, 380))
        
        return img, torch.tensor(label, dtype=torch.float)

    def _load_item(self, path, labels):
        img = torchvision.io.read_image(path)
        img = img.float()/255.0
        return img, torch.tensor(labels, dtype=torch.float32)

def get_transforms(config):
    img_size = config.get('img_size', 380)
    
    # 训练集增强
    train_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(15),  # 增加旋转角度
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05),  # 增强颜色变化
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 验证集增强
    val_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),  
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    return train_transform, val_transform