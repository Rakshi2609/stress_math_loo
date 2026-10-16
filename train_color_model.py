"""
PyTorch ML Model Training Script for Color Classification.
Generates an augmented dataset of RED, GREEN, BLUE, and BACKGROUND samples,
then trains the lightweight ColorClassifierCNN model and exports 'color_model.pth'.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import cv2
from vision_detector import ColorClassifierCNN

# Label mapping
CLASS_MAP = {
    0: "RED",
    1: "GREEN",
    2: "BLUE",
    3: "BACKGROUND"
}

class SyntheticColorDataset(Dataset):
    """
    Generates realistic 64x64 color patches with lighting variations,
    textures, noise, and shadows representing sponges and marker circles.
    """
    def __init__(self, samples_per_class=1000):
        self.data = []
        self.labels = []
        
        np.random.seed(42)

        for label in range(4):
            for _ in range(samples_per_class):
                patch = np.zeros((64, 64, 3), dtype=np.uint8)

                if label == 0:  # RED
                    # High red, lower green & blue
                    r = np.random.randint(140, 255)
                    g = np.random.randint(10, 70)
                    b = np.random.randint(10, 70)
                elif label == 1:  # GREEN
                    r = np.random.randint(10, 80)
                    g = np.random.randint(130, 255)
                    b = np.random.randint(10, 90)
                elif label == 2:  # BLUE
                    r = np.random.randint(10, 70)
                    g = np.random.randint(40, 120)
                    b = np.random.randint(150, 255)
                else:  # BACKGROUND (desk wood, white paper, shadows, grey)
                    base = np.random.randint(80, 230)
                    r = base + np.random.randint(-20, 20)
                    g = base + np.random.randint(-20, 20)
                    b = base + np.random.randint(-20, 20)

                # Fill with color base
                patch[:, :, 0] = np.clip(b, 0, 255)
                patch[:, :, 1] = np.clip(g, 0, 255)
                patch[:, :, 2] = np.clip(r, 0, 255)

                # Add texture / sponge noise & shadow gradient
                noise = np.random.normal(0, 15, (64, 64, 3))
                patch = np.clip(patch.astype(np.float32) + noise, 0, 255).astype(np.uint8)

                # Convert BGR to RGB and normalize to [0, 1]
                rgb = cv2.cvtColor(patch, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                tensor_img = torch.tensor(rgb).permute(2, 0, 1) # (C, H, W)

                self.data.append(tensor_img)
                self.labels.append(label)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

def train_model(save_path="color_model.pth", epochs=10, batch_size=32, lr=0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training on device: {device}")

    dataset = SyntheticColorDataset(samples_per_class=1200)
    train_size = int(0.85 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)

    model = ColorClassifierCNN(num_classes=4).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print(f"[*] Starting training for {epochs} epochs...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_acc = 100.0 * correct / total
        avg_loss = total_loss / total

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_acc = 100.0 * val_correct / val_total
        print(f"  Epoch [{epoch+1:02d}/{epochs:02d}] - Loss: {avg_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")

    # Save trained weights
    torch.save(model.state_dict(), save_path)
    print(f"[+] Model saved successfully to '{save_path}'!")
    return save_path

if __name__ == "__main__":
    train_model(save_path="/home/appu/intership/stress_math_lo/color_model.pth")
