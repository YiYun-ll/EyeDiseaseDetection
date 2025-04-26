import torch
import torch.nn as nn
from torchvision.models import efficientnet_b3,efficientnet_b4,efficientnet_b0,resnet50, densenet121



class CBAM(nn.Module):
    def __init__(self, in_channels, reduction_ratio=16):
        super(CBAM, self).__init__()
        # 通道注意力
        self.channel_attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, in_channels // reduction_ratio, kernel_size=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // reduction_ratio, in_channels, kernel_size=1, bias=False)
        )
        
        # 空间注意力
        self.spatial_attention = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False),
            nn.BatchNorm2d(1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # 通道注意力
        channel_attention = self.channel_attention(x)
        channel_attention = torch.sigmoid(channel_attention)
        x = x * channel_attention
        
        # 空间注意力
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        spatial_features = torch.cat([avg_out, max_out], dim=1)
        spatial_attention = self.spatial_attention(spatial_features)
        x = x * spatial_attention
        
        return x

class EyeDiseaseModel(nn.Module):
    def __init__(self,name, num_classes=8, pretrained=True,dropout_rate=0.5):
        super().__init__()
        # 根据 name 选择模型
        if name == "efficientnet-b3":
            self.base = efficientnet_b3(pretrained=pretrained)
            in_features = self.base.classifier[1].in_features
        elif name == "efficientnet-b4":
            self.base = efficientnet_b4(pretrained=pretrained)
            in_features = self.base.classifier[1].in_features
        elif name == "efficientnet-b0":
            self.base = efficientnet_b0(pretrained=pretrained)
            in_features = self.base.classifier[1].in_features
        elif name == "resnet50":
            self.base = resnet50(pretrained=pretrained)
            in_features = self.base.fc.in_features
        elif name == "densenet121":
            self.base = densenet121(pretrained=pretrained)
            in_features = self.base.classifier.in_features
        else:
            raise ValueError(f"Unsupported model name: {name}")

        # 移除原始分类器
        if "efficientnet" in name:
            # 保留特征提取部分，移除分类器
            self.features = nn.Sequential(*list(self.base.children())[:-1])
            self.base = None  # 释放内存
        elif "densenet" in name:
            self.features = nn.Sequential(*list(self.base.children())[:-1])
            self.base = None
        else:
            self.features = nn.Sequential(*list(self.base.children())[:-2])
            self.base = None
        
        # 添加CBAM注意力机制
        self.attention = CBAM(in_features)
        
        # 添加全局池化
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        # 添加自定义分类器，包含批归一化和dropout以提高泛化能力
        self.classifier = nn.Sequential(
            nn.BatchNorm1d(in_features),
            nn.Dropout(dropout_rate),
            nn.Linear(in_features, 512),
            nn.LeakyReLU(0.1, inplace=True),  
            nn.BatchNorm1d(512),
            nn.Dropout(dropout_rate * 0.8),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.1, inplace=True),
            nn.BatchNorm1d(256),
            nn.Dropout(dropout_rate * 0.6),
            nn.Linear(256, num_classes)
        )
        # 可学习的缩放因子，控制输出范围
        self.scale_factors = nn.Parameter(torch.ones(num_classes) * 3.0)
        self.bias_factors = nn.Parameter(torch.zeros(num_classes))
        # 初始化权重
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.classifier.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu',a=0.1)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        # 特征提取
        x = self.features(x)
        
        # 应用注意力机制
        x = self.attention(x)
        
        # 全局池化
        x = self.global_pool(x)
        x = torch.flatten(x, 1)
        
        # 分类
        logits = self.classifier(x)
        
        # 应用类别特定的缩放和偏置
        logits = logits * self.scale_factors + self.bias_factors
        return logits  

