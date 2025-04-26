import os
import random
import numpy as np
from PIL import Image, ImageEnhance


#输入图片数据增强
def medical_image_augmentation(input_dir, output_dir, num_augment_per_image):
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有图像文件
    img_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    for img_file in img_files:
        img_path = os.path.join(input_dir, img_file)
        
        # 读取图像并保留元数据
        img = Image.open(img_path)
        exif_data = img.info.get('exif', b'')
        dpi = img.info.get('dpi', (72, 72))  # 默认DPI为72

        # 转换为RGB模式处理（保留alpha通道信息）
        if img.mode != 'RGB':
            img = img.convert('RGB')

        for aug_idx in range(num_augment_per_image):
            # 克隆原始图像
            aug_img = img.copy()
            
            # 随机选择增强组合（确保至少应用一个变换）
            transform_sequence = random.sample(['rotate', 'shift', 'brightness', 'contrast','noise'], 
                                            k=random.randint(2, 3))
            
            # 应用变换
            for transform in transform_sequence:
                try:
                    if transform == 'rotate':
                        # 小角度旋转（±3度）
                        angle = random.choice([-3, -2, -1, 1, 2, 3])
                        aug_img = aug_img.rotate(angle, fillcolor=0, resample=Image.BILINEAR)

                    elif transform == 'shift':
                        # 微平移（±3%）
                        max_shift_x = int(aug_img.width * 0.03)
                        max_shift_y = int(aug_img.height * 0.03)
                        dx = random.randint(-max_shift_x, max_shift_x)
                        dy = random.randint(-max_shift_y, max_shift_y)
                        
                        aug_img = aug_img.transform(
                            aug_img.size,
                            Image.AFFINE,
                            (1, 0, dx, 0, 1, dy),
                            fillcolor=0
                        )

                    elif transform == 'brightness':
                        # 亮度调整（0.9-1.1）
                        enhancer = ImageEnhance.Brightness(aug_img)
                        aug_img = enhancer.enhance(random.uniform(0.9, 1.1))

                    elif transform == 'contrast':
                        # 对比度调整（0.95-1.05）
                        enhancer = ImageEnhance.Contrast(aug_img)
                        aug_img = enhancer.enhance(random.uniform(0.95, 1.05))

                    elif transform == 'noise':
                        # 高斯噪声（σ=0.5-1.5）
                        arr = np.array(aug_img)
                        noise = np.random.normal(0, random.uniform(0.5, 1.5), arr.shape)
                        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
                        aug_img = Image.fromarray(arr)

                except Exception as e:
                    print(f"Error applying {transform}: {str(e)}")
                    continue

            # 保存增强结果
            base_name = os.path.splitext(img_file)[0]
            output_path = os.path.join(output_dir, f"{base_name}_aug{aug_idx+1}.png")
            
            # 保留原始DPI和EXIF信息
            aug_img.save(
                output_path,
                format='PNG',
                quality=95,
                dpi=dpi,
                exif=exif_data
            )

if __name__ == "__main__":
    input_directory = "../InitalArgumentEye"       # 原始图片目录
    output_directory = "../AugmentEye"            # 输出目录
    augmentation_number =15                      # 每张原始图生成增强图片数量

    medical_image_augmentation(
        input_dir=input_directory,
        output_dir=output_directory,
        num_augment_per_image=augmentation_number
    )