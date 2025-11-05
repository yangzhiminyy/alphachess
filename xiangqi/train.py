import pickle
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from nn_example import make_simple_resnet
import numpy as np

# 数据集包装（兼容pkl自对弈样本）
class XiangqiDataset(Dataset):
    def __init__(self, data):
        # 每项：(planes[channels,10,9], policy[8100], value)
        x_np = np.asarray([d[0] for d in data], dtype=np.float32)
        pi_np = np.asarray([d[1] for d in data], dtype=np.float32)
        v_np = np.asarray([d[2] for d in data], dtype=np.float32)
        self.x = torch.from_numpy(x_np)
        self.pi = torch.from_numpy(pi_np)
        self.v = torch.from_numpy(v_np)
    def __len__(self):
        return len(self.x)
    def __getitem__(self, i):
        return self.x[i], self.pi[i], self.v[i]

def train(model, dataloader, optimizer, epochs=5, device='cpu'):
    model.train()
    ce_loss = nn.CrossEntropyLoss()
    mse_loss = nn.MSELoss()
    for epoch in range(epochs):
        total_loss = total_pi = total_v = 0.0
        n = 0
        for x, pi, v in dataloader:
            x = x.to(device, non_blocking=True)
            pi = pi.to(device, non_blocking=True)
            v = v.to(device, non_blocking=True)
            optimizer.zero_grad()
            logits, value = model(x)
            # policy loss (cross entropy between logits-softmax和pi目标
            target = pi.argmax(dim=1)
            loss_pi = ce_loss(logits, target)
            # value loss (均方误差)
            value = value.view(-1)
            loss_v = mse_loss(value, v)
            loss = loss_pi + loss_v
            loss.backward()
            optimizer.step()
            total_loss += loss.item()*x.size(0)
            total_pi += loss_pi.item()*x.size(0)
            total_v += loss_v.item()*x.size(0)
            n += x.size(0)
        print(f'Epoch {epoch+1} | total_loss={total_loss/n:.4f} | policy_loss={total_pi/n:.4f} | value_loss={total_v/n:.4f}')

def main():
    with open('selfplay_samples.pkl', 'rb') as f:
        data = pickle.load(f)
    dataset = XiangqiDataset(data)
    # Windows 上建议 num_workers=0；若在Linux可调大以提速
    loader = DataLoader(dataset, batch_size=32, shuffle=True, pin_memory=True, num_workers=0)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = make_simple_resnet(hidden=32).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    train(model, loader, optimizer, epochs=5, device=device)
    torch.save(model.state_dict(), 'xiq_model.pth')
    print('模型已保存为 xiq_model.pth')

if __name__ == '__main__':
    main()
