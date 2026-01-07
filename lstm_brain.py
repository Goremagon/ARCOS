import torch
import torch.nn as nn
import numpy as np
from sklearn.preprocessing import MinMaxScaler

class LSTMModel(nn.Module):
    def __init__(self, input_size=5, hidden_size=64, num_layers=2, output_size=1):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM Layer: The "Memory"
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        
        # Fully Connected Layer: The "Decision"
        self.fc = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid() # Outputs probability 0-1

    def forward(self, x):
        # Initialize hidden state with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # Forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))
        
        # Decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])
        return self.sigmoid(out)

def train_and_predict(df, window_size=60):
    """
    Trains a fresh LSTM on the fly using recent 15m candles.
    Returns: Probability (0.0 - 1.0)
    """
    # 1. Prepare Data
    # We use 5 features: Close, Volume, High-Low, Close-Open, SMA_5
    df = df.copy()
    df['Range'] = df['High'] - df['Low']
    df['Body'] = df['Close'] - df['Open']
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df.dropna(inplace=True)
    
    features = df[['Close', 'Volume', 'Range', 'Body', 'SMA_5']].values
    
    # Normalize (Crucial for Neural Nets)
    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(features)
    
    # 2. Create Sequences (Sliding Window)
    X, y = [], []
    for i in range(window_size, len(features_scaled)-1):
        X.append(features_scaled[i-window_size:i])
        # Target: 1 if next Close is higher, else 0
        is_higher = 1 if features_scaled[i+1][0] > features_scaled[i][0] else 0
        y.append(is_higher)
        
    if len(X) < 10: return 0.5 # Not enough data
    
    X_train = torch.tensor(np.array(X), dtype=torch.float32)
    y_train = torch.tensor(np.array(y), dtype=torch.float32).unsqueeze(1)
    
    # 3. Setup GPU (The 3090 Flex)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LSTMModel(input_size=5).to(device)
    X_train = X_train.to(device)
    y_train = y_train.to(device)
    
    # 4. Train (Fast Loop)
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    model.train()
    epochs = 50 # Fast training for real-time
    for _ in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        
    # 5. Predict Next Candle
    model.eval()
    last_sequence = features_scaled[-window_size:]
    last_tensor = torch.tensor(np.array([last_sequence]), dtype=torch.float32).to(device)
    
    with torch.no_grad():
        prediction = model(last_tensor).item()
        
    return prediction