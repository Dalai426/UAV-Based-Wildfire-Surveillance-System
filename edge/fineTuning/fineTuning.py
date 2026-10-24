#import torch
import torchvision
import torch.optim as optim
import torch.nn as nn

#define trainloader


EPOCHS = 50
LR = 0.0001

criterion = nn.BinaryCrossEntropyLoss()
optimizer = optim.adam(net.parameters(), lr=LR)
net = torchvision.models.mobilenet_v2(weights=torchvision.models.MobileNet_V2_Weights.DEFAULT)
#modify net last layers and freeze pretained weights

for epoch in range(EPOCHS):  
    running_loss = 0.0
    for i, data in enumerate(trainloader, 0):
        inputs, labels = data

        optimizer.zero_grad()

        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        if i % 2000 == 1999:    
            print(f'[{epoch + 1}, {i + 1:5d}] loss: {running_loss / 2000:.3f}')
            running_loss = 0.0

print('Finished Training')
