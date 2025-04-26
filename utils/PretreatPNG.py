# python
import os
import cv2
import argparse
from glob import glob
from tqdm import tqdm
import numpy as np

#单图片合成双眼图预处理
class ImagePreprocessor:
    def __init__(self, input_dir, output_dir, mode="dual", target_size=(380, 190)):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.mode = mode
        self.target_size = target_size  # (width, height)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def adjust_brightness(self, img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        cl = clahe.apply(l_channel)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    
    def resize_image(self, img):
        target_w, target_h = self.target_size
        h, w = img.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h))
        delta_w = target_w - new_w
        delta_h = target_h - new_h
        top = delta_h // 2
        bottom = delta_h - top
        left = delta_w // 2
        right = delta_w - left
        return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    
    def process_image(self, path):
        img = cv2.imread(path)
        if img is None:
            return None
        img = self.resize_image(img)
        return img

    def process_pair(self, left_path, right_path):
        left_img = self.process_image(left_path)
        right_img = self.process_image(right_path)
        if left_img is None or right_img is None:
            return None
        if self.mode == "dual":
            return (left_img, right_img)
        else:
            # 上下拼接：首先调整左右两张图像为相同宽度（已经resize到相同尺寸）则直接拼接
            return cv2.vconcat([left_img, right_img])
    
    def run(self):
        left_files = sorted(glob(os.path.join(self.input_dir, "*_left.*")))
        right_files = sorted(glob(os.path.join(self.input_dir, "*_right.*")))
        pairs = list(zip(left_files, right_files))
        print(f"Found {len(pairs)} valid pairs")
        for left_path, right_path in tqdm(pairs):
            result = self.process_pair(left_path, right_path)
            if result is None:
                continue
            base_name = os.path.basename(left_path).split("_left")[0]
            if self.mode == "dual":
                cv2.imwrite(os.path.join(self.output_dir, f"{base_name}_L.png"), result[0])
                cv2.imwrite(os.path.join(self.output_dir, f"{base_name}_R.png"), result[1])
            else:
                cv2.imwrite(os.path.join(self.output_dir, f"{base_name}.png"), result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="图片预处理")
    parser.add_argument("--input_dir", type=str, default="Training_Dataset", help="原始数据集目录")
    parser.add_argument("--output_dir", type=str, default="Processed_Dataset", help="处理后数据集目录")
    parser.add_argument("--mode", type=str, choices=["dual", "single"], default="dual", help="处理模式")
    parser.add_argument("--width", type=int, default=380, help="目标宽度")
    parser.add_argument("--height", type=int, default=190, help="目标高度")
    args = parser.parse_args()
    
    preprocessor = ImagePreprocessor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        mode=args.mode,
        target_size=(args.width, args.height)
    )
    preprocessor.run()