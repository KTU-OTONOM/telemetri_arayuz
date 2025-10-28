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
        
        # Mesafe takibi için
        self.last_time = time.time()
    
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
            print("📊 Veri gönderimi başladı...")
            return True
            
        except Exception as e:
            print(f"❌ Server başlatma hatası: {e}")
            return False
    
    def generate_data(self):
        """Gerçekçi telemetri verisi üret"""
        # Rastgele değişimler - daha gerçekçi (küçük adımlar)
        change = random.randint(-30, 40)  # Daha yumuşak değişimler
        self.erpm += change
        self.erpm = max(-3000, min(3000, self.erpm))  # Daha geniş aralık
        
        # RPM hesapla
        self.rpm = abs(self.erpm) // 14  # Gear ratio
        
        # Hız hesapla (km/h olarak)
        # Hız = RPM × tekerlek çapı × π / 60
        wheel_diameter_m = 0.5  # 50cm çaplı tekerlek
        self.speed = (abs(self.rpm) * wheel_diameter_m * 3.14159 * 60) / 1000
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
            f"{timestamp} -> Hız (km/h): {self.speed:.2f}",
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
        data_count = 0
        
        try:
            while self.is_running:
                if self.client_socket:
                    # Veri üret ve gönder
                    self.generate_data()
                    data = self.send_data_set()
                    
                    try:
                        self.client_socket.send(data.encode('utf-8'))
                        data_count += 1
                        
                        # Her 50 pakette bir özet bilgi göster (yaklaşık her 5 saniyede)
                        if data_count % 50 == 0:
                            print(f"📤 {data_count} veri paketi gönderildi | "
                                  f"Hız: {self.speed:.1f}km/h | "
                                  f"Akım: {self.current:.1f}A | "
                                  f"Güç: {self.power:.1f}W")
                    except (ConnectionResetError, BrokenPipeError):
                        print("🔌 Bağlantı kesildi!")
                        break
                
                time.sleep(0.1)  # 100ms (0.1 saniye) bekle - 10 paket/saniye
                
        except KeyboardInterrupt:
            print(f"\n⏹️ Simülasyon durduruldu. Toplam {data_count} veri paketi gönderildi.")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.is_running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
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
        change = random.randint(-50, 50)
        self.erpm += change
        self.erpm = max(-2000, min(2000, self.erpm))
        
        self.rpm = abs(self.erpm) // 14
        
        # Hız hesaplama (km/h)
        wheel_diameter_m = 0.5
        self.speed = (abs(self.rpm) * wheel_diameter_m * 3.14159 * 60) / 1000
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
            data_count = 0
            
            try:
                while time.time() - start_time < duration:
                    self.generate_data()
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    lines = [
                        f"{timestamp} -> ----- ALINAN VERİ -----",
                        f"{timestamp} -> ERPM: {int(self.erpm)}",
                        f"{timestamp} -> RPM: {int(self.rpm)}",
                        f"{timestamp} -> Hız (km/h): {self.speed:.2f}",
                        f"{timestamp} -> Akım (A): {self.current:.2f}",
                        f"{timestamp} -> Duty: {int(self.duty)}",
                        f"{timestamp} -> Gerilim (V): {self.voltage:.2f}",
                        f"{timestamp} -> Güç (W): {self.power:.2f}",
                        ""
                    ]
                    
                    for line in lines:
                        f.write(line + "\n")
                    
                    data_count += 1
                    
                    # Her 50 pakette bir konsola bilgi yazdır
                    if data_count % 50 == 0:
                        print(f"📝 {data_count} veri paketi yazıldı...")
                    
                    f.flush()  # Hemen dosyaya yaz
                    time.sleep(0.1)  # 100ms bekle - 10 paket/saniye
                    
            except KeyboardInterrupt:
                print("\n⏹️ Simülasyon durduruldu.")
        
        print(f"✅ Simülasyon tamamlandı. Toplam {data_count} veri paketi.")
        print(f"📁 Veriler: {self.filename}")


def main():
    print("🚀 Arduino Telemetri Simulatörü v3.1 (Hızlı Mod)")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("Kullanım modları:")
        print("1. tcp    - TCP server modu (önerilen)")
        print("2. file   - Dosya modu")
        print()
        mode = input("Mod seçin (tcp/file) [tcp]: ").lower() or 'tcp'
    
    if mode == 'tcp':
        # TCP server modu
        host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
        
        print(f"\n🔧 Ayarlar:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Hız: 10 paket/saniye (100ms aralık)")
        print(f"\n💡 Bağlantı komutu:")
        print(f"   Telemetri arayüzünde 'socket://{host}:{port}' seçin")
        print()
        
        simulator = VirtualSerialSimulator(host, port)
        simulator.run_simulation()
        
    elif mode == 'file':
        # Dosya modu
        filename = sys.argv[2] if len(sys.argv) > 2 else "arduino_data.txt"
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        
        print(f"\n🔧 Ayarlar:")
        print(f"   Dosya: {filename}")
        print(f"   Süre: {duration} saniye")
        print(f"   Hız: 10 paket/saniye (100ms aralık)")
        print()
        
        simulator = FileSimulator(filename)
        simulator.run_simulation(duration)
        
    else:
        print("❌ Geçersiz mod! tcp veya file seçin.")


if __name__ == '__main__':
    main()