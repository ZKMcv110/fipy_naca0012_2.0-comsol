import numpy as np

data = np.load('field_data/case_20001_full.npz')
print('=== 数据统计 ===')
print(f'温度范围: {data["T"].min():.2f} - {data["T"].max():.2f}')
print(f'u速度范围: {data["u"].min():.4f} - {data["u"].max():.4f}')
print(f'v速度范围: {data["v"].min():.4f} - {data["v"].max():.4f}')
print(f'压力范围: {data["p"].min():.2f} - {data["p"].max():.2f}')
print(f'空气域点数: {(data["domain"]==0).sum()}')
print(f'固体域点数: {(data["domain"]==1).sum()}')
print(f'空气域温度: {data["T"][data["domain"]==0].min():.2f} - {data["T"][data["domain"]==0].max():.2f}')
print(f'固体域温度: {data["T"][data["domain"]==1].min():.2f} - {data["T"][data["domain"]==1].max():.2f}')
