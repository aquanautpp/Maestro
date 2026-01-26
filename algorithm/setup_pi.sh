#!/bin/bash
# Setup do Maestro no Raspberry Pi Zero 2 W
#
# Uso:
#   curl -sSL https://raw.githubusercontent.com/.../setup_pi.sh | bash
#   ou
#   chmod +x setup_pi.sh && ./setup_pi.sh

set -e

echo "========================================"
echo "MAESTRO - Setup para Pi Zero 2 W"
echo "========================================"

# Atualiza sistema
echo "[1/5] Atualizando sistema..."
sudo apt-get update
sudo apt-get upgrade -y

# Instala dependências de áudio
echo "[2/5] Instalando dependências de áudio..."
sudo apt-get install -y \
    python3-pip \
    python3-numpy \
    portaudio19-dev \
    python3-pyaudio \
    libatlas-base-dev

# Instala pacotes Python
echo "[3/5] Instalando pacotes Python..."
pip3 install --user \
    sounddevice \
    numpy \
    flask

# Habilita I2S (para INMP441)
echo "[4/5] Configurando I2S..."
if ! grep -q "dtparam=i2s=on" /boot/config.txt; then
    echo "dtparam=i2s=on" | sudo tee -a /boot/config.txt
    echo "I2S habilitado (reboot necessário)"
fi

# Cria serviço systemd para iniciar automaticamente
echo "[5/5] Criando serviço..."
sudo tee /etc/systemd/system/maestro.service > /dev/null << 'EOF'
[Unit]
Description=Maestro Turn Detector
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/maestro
ExecStart=/usr/bin/python3 /home/pi/maestro/pi_detector.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Cria diretório
mkdir -p ~/maestro

echo ""
echo "========================================"
echo "Setup completo!"
echo "========================================"
echo ""
echo "Próximos passos:"
echo ""
echo "1. Copie pi_detector.py para ~/maestro/"
echo "   scp pi_detector.py pi@<ip>:~/maestro/"
echo ""
echo "2. Conecte o hardware:"
echo "   - Microfone USB ou INMP441"
echo "   - Motor no GPIO 17"
echo ""
echo "3. Teste manualmente:"
echo "   python3 ~/maestro/pi_detector.py"
echo ""
echo "4. (Opcional) Habilite início automático:"
echo "   sudo systemctl enable maestro"
echo "   sudo systemctl start maestro"
echo ""
echo "5. Acesse o dashboard:"
echo "   http://<ip-do-pi>:5000"
echo ""
