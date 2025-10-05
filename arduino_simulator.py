#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arduino Telemetri Simulatörü
Test amaçlı Arduino verilerini simüle eder
"""

import serial
import time
import random
from datetime import datetime

class ArduinoSimulator:
    def __init__(self, port='COM1', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
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
        """Gerçekçi telemetri verisi üret"""
        # ERPM değişimi (daha yumuşak geçişler)
        change = random.randint(-30, 30)
        self.erpm += change
        self.erpm = max(-1500, min(1500, self.erpm))
        
        # RPM hesaplama (ERPM'den türetilmiş)
        self.rpm = abs(self.erpm) // 12
        
        # Hız hesaplama (RPM'e dayalı, km/h)
        self.speed = abs(self.rpm) * 0.05
        self.speed = max(0, min(60, self.speed))
        
        # Akım değişimi (hıza bağlı)
        base_current = abs(self.speed * 0.1)
        self.current = base_current + random.uniform(-2.0, 2.0)
        self.current = max(-10.0, min(15.0, self.current))
        
        # Duty cycle (hıza bağlı)
        base_duty = min(80, abs(self.speed * 1.5))
        self.duty = int(base_duty + random.randint(-5, 5))
        self.duty = max(0, min(100, self.duty))
        
        # Gerilim (küçük dalgalanmalar)
        self.voltage = 19.2 + random.uniform(-0.5, 0.8)
        
        # Güç hesaplama (gerilim x akım)
        self.power = self.voltage * self.current
        
    def format_data_line(self, data_type, value, unit=""):
        """Veri satırını Arduino formatında oluştur"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if unit:
            return f"{timestamp} -> {data_type}: {value}\n"
        else:
            return f"{timestamp} -> {data_type}: {value}\n"
    
    def send_data_set(self):
        """Bir set veri gönder"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        lines = [
            f"{timestamp} -> ----- ALINAN VERİ -----\n",
            self.format_data_line("ERPM", int(self.erpm)),
            self.format_data_line("RPM", int(self.rpm)),
            self.format_data_line("Hız (km/s)", f"{self.speed:.2f}"),
            self.format_data_line("Akım (A)", f"{self.current:.2f}"),
            self.format_data_line("Duty", int(self.duty)),
            self.format_data_line("Gerilim (V)", f"{self.voltage:.2f}"),
            self.format_data_line("Güç (W)", f"{self.power:.2f}"),
            "\n"
        ]
        
        return lines
    
    def run_simulation(self, duration=None):
        """Simülasyonu çalıştır"""
        print("=" * 50)
        print("   ARDUINO TELEMETRİ SİMÜLATÖRÜ")
        print("=" * 50)
        print(f"📡 Seri Port: {self.port}")
        print(f"⚡ Baudrate: {self.baudrate}")
        if duration:
            print(f"⏱️  Test Süresi: {duration} saniye")
        else:
            print("⏱️  Sürekli çalışma modu")
        print("🛑 Ctrl+C ile durdurmak için...")
        print("=" * 50)
        print()
        
        start_time = time.time()
        data_count = 0
        
        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    break
                    
                self.generate_data()
                lines = self.send_data_set()
                
                for line in lines:
                    print(line.strip())
                
                data_count += 1
                time.sleep(1)  # 1 saniye bekle
                
        except KeyboardInterrupt:
            print()
            print("=" * 50)
            print("🛑 Simülasyon kullanıcı tarafından durduruldu")
            print(f"📊 Toplam {data_count} veri seti gönderildi")
            print(f"⏱️  Çalışma süresi: {time.time() - start_time:.1f} saniye")
            print("=" * 50)

def main():
    import sys
    
    # Komut satırı argümanları
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    simulator = ArduinoSimulator(port, baudrate)
    simulator.run_simulation(duration)

if __name__ == '__main__':
    main()