"""
绘梨衣 · VoiceAE V3 — 数据增强 + 深度训练
从6句→30+句，更深模型，2000轮
"""
import torch, torch.nn as nn, torchaudio, librosa, numpy as np, soundfile as sf
from pathlib import Path

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
AUG_DIR = BASE / "data" / "augmented"
OUTPUT_DIR = BASE / "GPT-SoVITS" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUG_DIR.mkdir(exist_ok=True)

DEVICE = "cpu"
SR = 22050
N_FFT = 512
HOP = 256
N_FREQ = N_FFT // 2 + 1
EPOCHS = 2000
BATCH_SIZE = 2  # CPU keeps small


# ═══════ 残差块 ═══════
class ResBlock(nn.Module):
    def __init__(self, ch, dilation=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(ch, ch, 3, padding=dilation, dilation=dilation),
            nn.BatchNorm1d(ch), nn.ReLU(),
            nn.Conv1d(ch, ch, 3, padding=1), nn.BatchNorm1d(ch),
        )
    def forward(self, x):
        return torch.relu(x + self.conv(x))


# ═══════ V3 更深模型 ═══════
class VoiceAEV3(nn.Module):
    def __init__(self):
        super().__init__()
        # Encoder: 257 → 256 → 128 → 64 → 32
        self.enc_in = nn.Conv1d(N_FREQ, 256, 7, padding=3)
        self.enc_res1 = ResBlock(256)
        self.enc_down1 = nn.Conv1d(256, 128, 4, stride=2, padding=1)
        self.enc_res2a = ResBlock(128)
        self.enc_res2b = ResBlock(128)  # extra depth
        self.enc_down2 = nn.Conv1d(128, 64, 4, stride=2, padding=1)
        self.enc_res3a = ResBlock(64)
        self.enc_res3b = ResBlock(64)   # extra depth
        self.enc_down3 = nn.Conv1d(64, 32, 4, stride=2, padding=1)
        self.enc_res4 = ResBlock(32)

        self.latent = nn.Linear(32, 64)

        # Decoder: 32 → 64 → 128 → 256 → 257
        self.dec_up1 = nn.ConvTranspose1d(64, 64, 4, stride=2, padding=1)
        self.dec_res1a = ResBlock(64)
        self.dec_res1b = ResBlock(64)
        self.dec_up2 = nn.ConvTranspose1d(64, 128, 4, stride=2, padding=1)
        self.dec_res2a = ResBlock(128)
        self.dec_res2b = ResBlock(128)
        self.dec_up3 = nn.ConvTranspose1d(128, 256, 4, stride=2, padding=1)
        self.dec_res3 = ResBlock(256)
        self.dec_out = nn.Conv1d(256, N_FREQ, 7, padding=3)

    def forward(self, x):
        b, f, t_in = x.shape
        # Pad to be divisible by 8 (3 downsampling steps)
        pad = (8 - t_in % 8) % 8
        if pad > 0:
            x = torch.nn.functional.pad(x, (0, pad))

        h = torch.relu(self.enc_in(x))
        h = self.enc_res1(h)
        h = torch.relu(self.enc_down1(h))
        h = self.enc_res2a(h); h = self.enc_res2b(h)
        h = torch.relu(self.enc_down2(h))
        h = self.enc_res3a(h); h = self.enc_res3b(h)
        h = torch.relu(self.enc_down3(h))
        h = self.enc_res4(h)

        z = h.mean(dim=2); z = self.latent(z)
        t = h.shape[2]
        z = z.unsqueeze(-1).repeat(1, 1, t)

        h = torch.relu(self.dec_up1(z))
        h = self.dec_res1a(h); h = self.dec_res1b(h)
        h = torch.relu(self.dec_up2(h))
        h = self.dec_res2a(h); h = self.dec_res2b(h)
        h = torch.relu(self.dec_up3(h))
        h = self.dec_res3(h)
        out = self.dec_out(h)
        return out[:, :, :t_in]


# ═══════ 音频工具 ═══════
def load_audio(path, sr=SR):
    y, _ = librosa.load(str(path), sr=sr)
    return torch.from_numpy(y).float()

def linear_spec(y_t):
    spec = torch.stft(y_t, n_fft=N_FFT, hop_length=HOP,
                      window=torch.hann_window(N_FFT), return_complex=True)
    return torch.log(torch.clamp(spec.abs() + 1e-6, min=1e-6))


# ═══════ 数据增强 ═══════
def augment_audio(y: torch.Tensor):
    """从1个音频生成5个变体"""
    augmented = []
    y_np = y.numpy()
    for shift in [-3, -1.5, 1.5, 3]:
        ya = librosa.effects.pitch_shift(y_np, sr=SR, n_steps=shift)
        augmented.append(torch.from_numpy(ya).float())
    for rate in [0.9, 1.1]:
        ya = librosa.effects.time_stretch(y_np, rate=rate)
        # 保持原长度
        if len(ya) > len(y_np):
            ya = ya[:len(y_np)]
        else:
            ya = np.pad(ya, (0, len(y_np)-len(ya)))
        augmented.append(torch.from_numpy(ya).float())
    return augmented


# ═══════ 训练 ═══════
def train():
    print("=" * 55)
    print("  绘梨衣 · VoiceAE V3 数据增强+深度训练")
    print(f"  {N_FREQ}bin | 8 ResBlocks | 2000 epochs")
    print("=" * 55)

    # 加载原始+增强
    wav_files = sorted(DATA_DIR.glob("sentence_*.wav"))
    if not wav_files:
        wav_files = sorted((DATA_DIR / "eriyi").glob("sentence_*.wav"))

    specs = []
    clip_count = 0
    for w in wav_files:
        y = load_audio(w)
        specs.append(linear_spec(y).unsqueeze(0))
        clip_count += 1
        # 增强
        for ay in augment_audio(y):
            specs.append(linear_spec(ay).unsqueeze(0))
            clip_count += 1

    min_t = min(s.shape[2] for s in specs)
    X = torch.cat([s[:, :, :min_t] for s in specs])
    print(f"  数据: {X.shape} ({len(wav_files)}原始×7 → {clip_count} clips)")

    model = VoiceAEV3().to(DEVICE)
    params = sum(p.numel() for p in model.parameters())
    print(f"  参数: {params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    mse = nn.MSELoss()
    l1 = nn.L1Loss()

    best_loss = float("inf")
    dataset = X.split(BATCH_SIZE)

    for e in range(EPOCHS):
        model.train()
        total_loss = 0
        for batch in dataset:
            optimizer.zero_grad()
            recon = model(batch)
            loss = mse(recon, batch) + 0.05 * l1(recon, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()

        avg_loss = total_loss / len(dataset)
        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.state_dict(), OUTPUT_DIR / "eriyi_voice_best.pth")

        if (e + 1) % 200 == 0:
            print(f"  {e+1:4d}/{EPOCHS}  loss={avg_loss:.6f}  best={best_loss:.6f}")

    print(f"\n  最佳loss: {best_loss:.6f}")
    torch.save(model.state_dict(), OUTPUT_DIR / "eriyi_voice.pth")
    print(f"  ✅ 保存: {OUTPUT_DIR / 'eriyi_voice.pth'}")

    # 生成样本
    with torch.no_grad():
        model.eval()
        gen = model(X[0:1]).squeeze(0)
        # Griffin-Lim高质量还原
        mag = torch.exp(gen) - 1e-6
        angles = torch.rand_like(mag) * 2 * np.pi
        spec = mag * torch.exp(1j * angles)
        win = torch.hann_window(N_FFT)
        for _ in range(50):
            wav = torch.istft(spec, n_fft=N_FFT, hop_length=HOP, window=win)
            stft = torch.stft(wav, n_fft=N_FFT, hop_length=HOP, window=win, return_complex=True)
            spec = mag * torch.exp(1j * stft.angle())
        sf.write(str(OUTPUT_DIR / "eriyi_sample.wav"), wav.numpy(), SR)
        print(f"  🎵 样本: output/eriyi_sample.wav ({len(wav)/SR:.1f}s)")

    print("=" * 55)
    print(f"  VoiceAE V3 训练完成! params={params:,} best_loss={best_loss:.6f}")
    print("=" * 55)


if __name__ == "__main__":
    train()
