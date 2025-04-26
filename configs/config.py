class Config:
    CSV_PATH = "../data/category.csv"       # 原始标注文件路径
    DATA_ROOT = "../data/raw"          # 图片根目录
    SPLIT_DIR = "../data/processed"          # 划分结果保存路径
    CLASS_NAMES = ['normal', 'diabetes', 'glaucoma', 'cataract', 'amd', 'hypertension', 'myopia', 'other']
    LABEL_MAPPING = {
        '0': '正常',
        '1': '糖尿病',
        '2': '青光眼',
        '3': '白内障',
        '4': 'AMD', 
        '5': '高血压',
        '6': '近视',
        '7': '其他'
    }
    IMAGE_SIZE = (300, 300)            # 输入尺寸
    BATCH_SIZE = 32