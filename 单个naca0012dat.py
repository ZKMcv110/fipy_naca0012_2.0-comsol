import numpy as np
import argparse
import os

class ThetaParameters:
    """定义参数结构体，保留全部6个参数以维持逻辑一致性"""
    def __init__(self, Tt=0.75, Ts=1.0, Ta=0.0, Tad=0.5, Twa=0.5, Tb=0.12):
        self.Tt = Tt    # 横向间距系数 (单翼型时不影响形状)
        self.Ts = Ts    # 纵向间距系数 (单翼型时不影响形状)
        self.Ta = Ta    # 弯度系数
        self.Tad = Tad  # 交错间距系数 (单翼型时不影响形状)
        self.Twa = Twa  # 最大弯度位置系数 (宽长比)
        self.Tb = Tb    # 厚度系数

def generate_and_write_airfoil(fp, x_center, y_center, chord_length, m, p, t):
    """
    生成单个自定义翼型并写入文件
    
    Args:
        fp: 文件指针
        x_center: 翼型起始点X坐标 (建议设为0)
        y_center: 翼型中心线Y坐标 (建议设为0)
        chord_length: 弦长
        m: 最大弯度
        p: 最大弯度位置
        t: 最大厚度
    """
    N = 201  # 采样点数
    
    x = np.linspace(0, chord_length, N)
    x_c = x / chord_length
    
    # 1. 计算厚度分布 (NACA 4位数公式)
    yt = (t / 0.2) * (0.2969 * np.sqrt(x_c) - 0.1260 * x_c - 0.3516 * x_c**2 + 
                      0.2843 * x_c**3 - 0.1015 * x_c**4)
    yt *= chord_length
    
    # 2. 计算弯度线 yc 和斜率 dyc/dx
    yc = np.zeros(N)
    dyc_dx = np.zeros(N)
    
    if m > 0:
        for i in range(N):
            if x_c[i] < (p / chord_length if chord_length !=0 else 1):
                # 这里根据你的逻辑 p 是物理长度，所以比较时需要除以弦长
                limit = p / chord_length
                yc[i] = (m / (limit**2)) * (2 * limit * x_c[i] - x_c[i]**2)
                dyc_dx[i] = (m / (limit**2)) * (2 * limit - 2 * x_c[i])
            else:
                limit = p / chord_length
                yc[i] = (m / ((1-limit)**2)) * ((1-2*limit) + 2*limit * x_c[i] - x_c[i]**2)
                dyc_dx[i] = (m / ((1-limit)**2)) * (2*limit - 2 * x_c[i])
        yc *= chord_length
        # 注意：dyc_dx 已经是无量纲斜率，不需要额外乘以弦长
    
    # 3. 计算上下翼面坐标 (考虑弯度线法向偏移)
    theta = np.arctan(dyc_dx)
    sin_theta = np.sin(theta)
    cos_theta = np.cos(theta)
    
    xu = x - yt * sin_theta
    yu = yc + yt * cos_theta
    xl = x + yt * sin_theta
    yl = yc - yt * cos_theta
    
    # 4. 强制后缘闭合
    yu[-1] = yl[-1] = 0.0
    xu[-1] = xl[-1] = chord_length
    
    # 5. 写入数据 (按顺时针或逆时针顺序，方便COMSOL识别封闭曲线)
    # 先写上表面 (从前向后)
    for i in range(N):
        fp.write(f"{xu[i] + x_center:.8f}\t{yu[i] + y_center:.8f}\n")
    
    # 再写下表面 (从后向前，避开重复的后缘点)
    for i in range(N-2, -1, -1):
        fp.write(f"{xl[i] + x_center:.8f}\t{yl[i] + y_center:.8f}\n")
    
    # 最后回到起点闭合
    fp.write(f"{xu[0] + x_center:.8f}\t{yu[0] + y_center:.8f}\n")

def main():
    """主函数：仅生成一个翼型"""
    parser = argparse.ArgumentParser(description='生成单个自定义翼型数据')
    parser.add_argument('--Ta', type=float, default=0.0, help='弯度系数')
    parser.add_argument('--Twa', type=float, default=0.5, help='最大弯度位置系数')
    parser.add_argument('--Tb', type=float, default=0.12, help='厚度系数')
    parser.add_argument('--scale', type=float, default=1.0, help='弦长(La)')
    parser.add_argument('--output', type=str, default="single_airfoil.dat", help='输出文件名')
    
    args = parser.parse_args()
    
    # 基本长度单位
    La = args.scale
    chord_length = La
    
    # 形状参数计算 (遵循你的逻辑)
    m = args.Ta * La
    p = args.Twa * La
    t = args.Tb * La
    
    filename = args.output
    with open(filename, "w") as fp:
        print(f"🚀 正在生成单个翼型数据...")
        print(f"参数配置: Camber={args.Ta}, Thickness={args.Tb}, MaxCamberPos={args.Twa}, Chord={La}")
        
        # 将翼型放置在 (0,0) 开始的位置，方便在 COMSOL 中阵列
        generate_and_write_airfoil(fp, 0, 0, chord_length, m, p, t)
    
    print(f"✅ 数据已导出至: {os.path.abspath(filename)}")
    print("💡 提示：在 COMSOL 中使用“插值曲线”导入此文件，然后添加“阵列”节点即可生成 3x8 结构。")

if __name__ == "__main__":
    main()