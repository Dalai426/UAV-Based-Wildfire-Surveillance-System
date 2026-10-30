import torch
import torch.optim as optim
import torch.nn as nn

def run_epoch(model, loader, criterion, optimizer=None, device=None):
    if device is None:
        device = next(model.parameters()).device

    isTrain = optimizer is not None
    model.train() if isTrain else model.eval()

    totalLoss, correct, total = 0.0, 0, 0

    with torch.set_grad_enabled(isTrain):
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device).float().unsqueeze(1)

            if isTrain:
                optimizer.zero_grad()

            outputs = model(inputs)
            loss = criterion(outputs, labels)

            if isTrain:
                loss.backward()
                optimizer.step()

            totalLoss += loss.item() * labels.size(0)
            correct += ((outputs >= 0.5) == labels).sum().item()
            total += labels.size(0)

    return totalLoss / total, correct / total