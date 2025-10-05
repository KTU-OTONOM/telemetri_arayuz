#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gelişmiş Arduino Telemetri Simulatörü
Virtual seri port oluşturur veya dosya üzerinden simülasyon yapar
"""

import sys
import time
import random
import threading
from datetime import datetime
import socket
import select

class VirtualSerialSimulator:
    """TCP socket tabanlı virtual seri port simulatörü"""
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.is_running = False
        self.server_socket = None
        self.client_socket = None
        
        # Simülasyon parametreleri
        self.erpm = 0
        self.rpm = 0
        self.speed = 0.0
        self.current = 0.0
        self.duty = 0
        self.voltage = 19.5
        self.power = 0.0
        
    def start_server(self):
        """TCP server başlat"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            print(f"🌐 Virtual Arduino Server başlatıldı: {self.host}:{self.port}")
            print(f"📡 Telemetri arayüzünde TCP bağlantısı için: socket://{self.host}:{self.port}")
            print("⏳ Bağlantı bekleniyor...")
            
            self.client_socket, addr = self.server_socket.accept()
            print(f"✅ Bağlantı kuruldu: {addr}")
            return True
            
        except Exception as e:
            print(f"❌ Server başlatma hatası: {e}")
            return False
    
    def generate_data(self):
        """Gerçekçi telemetri verisi üret"""
        # Rastgele değişimler - daha gerçekçi
        self.erpm += random.randint(-50, 50)
        self.erpm = max(-2000, min(2000, self.erpm))
        
        # RPM hesapla
        self.rpm = abs(self.erpm) // 14  # Gear ratio
        
        # Hız hesapla (km/h olarak)
        self.speed = abs(self.erpm) * 0.008
        self.speed = max(0, min(80, self.speed))
        
        # Akım hesapla (yük ile ilişkili)
        base_current = abs(self.erpm) * 0.002
        self.current = base_current + random.uniform(-0.5, 0.5)
        self.current = max(-10.0, min(20.0, self.current))
        
        # Duty cycle
        if abs(self.erpm) > 10:
            self.duty = min(100, abs(self.erpm) // 20 + random.randint(-5, 5))
        else:
            self.duty = 0
        self.duty = max(0, min(100, self.duty))
        
        # Gerilim (batarya voltajı simülasyonu)
        self.voltage = 19.5 + random.uniform(-0.8, 0.3)
        if self.current > 5:  # Yüksek akımda voltaj düşer
            self.voltage -= (self.current - 5) * 0.1
        self.voltage = max(16.0, min(21.0, self.voltage))
        
        # Güç hesapla
        self.power = self.voltage * self.current
    
    def send_data_set(self):
        """Bir set veri oluştur ve gönder"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        lines = [
            f"{timestamp} -> ----- ALINAN VERİ -----",
            f"{timestamp} -> ERPM: {int(self.erpm)}",
            f"{timestamp} -> RPM: {int(self.rpm)}",
            f"{timestamp} -> Hız (km/s): {self.speed:.2f}",
            f"{timestamp} -> Akım (A): {self.current:.2f}",
            f"{timestamp} -> Duty: {int(self.duty)}",
            f"{timestamp} -> Gerilim (V): {self.voltage:.2f}",
            f"{timestamp} -> Güç (W): {self.power:.2f}",
            ""
        ]
        
        return "\n".join(lines) + "\n"
    
    def run_simulation(self):
        """Simülasyonu çalıştır"""
        if not self.start_server():
            return
            
        self.is_running = True
        
        try:
            while self.is_running:
                if self.client_socket:
                    # Veri üret ve gönder
                    self.generate_data()
                    data = self.send_data_set()
                    
                    try:
                        self.client_socket.send(data.encode('utf-8'))
                        print(f"📤 Veri gönderildi: ERPM={int(self.erpm)}, Hız={self.speed:.1f}km/h, Akım={self.current:.1f}A")
                    except (ConnectionResetError, BrokenPipeError):
                        print("🔌 Bağlantı kesildi!")
                        break
                
                time.sleep(1)  # 1 saniye bekle
                
        except KeyboardInterrupt:
            print("\n⏹️ Simülasyon durduruldu.")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.is_running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        print("🧹 Temizlik tamamlandı.")

class FileSimulator:
    """Dosya tabanlı simulatör - test amaçlı"""
    
    def __init__(self, filename="arduino_data.txt"):
        self.filename = filename
        self.is_running = False
        
        # Simülasyon parametreleri
        self.erpm = 0
        self.rpm = 0
        self.speed = 0.0
        self.current = 0.0
        self.duty = 0
        self.voltage = 19.5
        self.power = 0.0
    
    def generate_data(self):
        """VirtualSerialSimulator ile aynı veri üretimi"""
        self.erpm += random.randint(-50, 50)
        self.erpm = max(-2000, min(2000, self.erpm))
        
        self.rpm = abs(self.erpm) // 14
        self.speed = abs(self.erpm) * 0.008
        self.speed = max(0, min(80, self.speed))
        
        base_current = abs(self.erpm) * 0.002
        self.current = base_current + random.uniform(-0.5, 0.5)
        self.current = max(-10.0, min(20.0, self.current))
        
        if abs(self.erpm) > 10:
            self.duty = min(100, abs(self.erpm) // 20 + random.randint(-5, 5))
        else:
            self.duty = 0
        self.duty = max(0, min(100, self.duty))
        
        self.voltage = 19.5 + random.uniform(-0.8, 0.3)
        if self.current > 5:
            self.voltage -= (self.current - 5) * 0.1
        self.voltage = max(16.0, min(21.0, self.voltage))
        
        self.power = self.voltage * self.current
    
    def run_simulation(self, duration=60):
        """Dosyaya veri yaz"""
        print(f"📄 Dosya simülasyonu başladı: {self.filename}")
        print(f"⏱️ Süre: {duration} saniye")
        print("📝 Veriler dosyaya yazılıyor...")
        
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("Arduino Telemetri Simülasyon Verileri\n")
            f.write("=" * 50 + "\n\n")
            
            start_time = time.time()
            
            try:
                while time.time() - start_time < duration:
                    self.generate_data()
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    lines = [
                        f"{timestamp} -> ----- ALINAN VERİ -----",
                        f"{timestamp} -> ERPM: {int(self.erpm)}",
                        f"{timestamp} -> RPM: {int(self.rpm)}",
                        f"{timestamp} -> Hız (km/s): {self.speed:.2f}",
                        f"{timestamp} -> Akım (A): {self.current:.2f}",
                        f"{timestamp} -> Duty: {int(self.duty)}",
                        f"{timestamp} -> Gerilim (V): {self.voltage:.2f}",
                        f"{timestamp} -> Güç (W): {self.power:.2f}",
                        ""
                    ]
                    
                    for line in lines:
                        f.write(line + "\n")
                        print(line)
                    
                    f.flush()  # Hemen dosyaya yaz
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Simülasyon durduruldu.")
        
        print(f"✅ Simülasyon tamamlandı. Veriler: {self.filename}")

def main():
    print("🚀 Arduino Telemetri Simulatörü v2.0")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("Kullanım modları:")
        print("1. python arduino_simulator.py tcp    - TCP server modu")
        print("2. python arduino_simulator.py file   - Dosya modu")
        print("3. python arduino_simulator.py console - Konsol modu")
        print()
        mode = input("Mod seçin (tcp/file/console) [tcp]: ").lower() or 'tcp'
    
    if mode == 'tcp':
        # TCP server modu
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
        
        simulator = VirtualSerialSimulator(host, port)
        simulator.run_simulation()
        
    elif mode == 'file':
        # Dosya modu
        filename = sys.argv[2] if len(sys.argv) > 2 else "arduino_data.txt"
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        
        simulator = FileSimulator(filename)
        simulator.run_simulation(duration)
        
    elif mode == 'console':
        # Konsol modu (eski versiyon)
        from arduino_simulator import ArduinoSimulator
        simulator = ArduinoSimulator()
        simulator.run_simulation()
        
    else:
        print("❌ Geçersiz mod! tcp, file veya console seçin.")

if __name__ == '__main__':
    main()