#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telemetri JSON Dosyası Analiz Aracı
Datetime anahtarlı JSON dosyalarını okur ve analiz eder
"""

import json
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

class TelemetryAnalyzer:
    def __init__(self, json_file):
        self.json_file = json_file
        self.data = None
        self.df = None
        
    def load_data(self):
        """JSON dosyasını yükle"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            print(f"✅ JSON dosyası yüklendi: {self.json_file}")
            
            # Export bilgilerini göster
            if 'export_info' in self.data:
                info = self.data['export_info']
                print(f"📊 Export Zamanı: {info.get('export_time', 'Bilinmiyor')}")
                print(f"📈 Toplam Kayıt: {info.get('total_records', 0)}")
                print(f"📋 Veri Tipleri: {', '.join(info.get('data_types', []))}")
                print(f"🗂️ Format: {info.get('format', 'Bilinmiyor')}")
                print()
            
            return True
            
        except Exception as e:
            print(f"❌ JSON dosyası yüklenirken hata: {e}")
            return False
    
    def convert_to_dataframe(self):
        """JSON verisini pandas DataFrame'e dönüştür"""
        if not self.data or 'data' not in self.data:
            print("❌ Veri bulunamadı!")
            return False
        
        records = []
        for datetime_str, record in self.data['data'].items():
            # Datetime'ı index olarak kullan
            record_copy = record.copy()
            record_copy['datetime_str'] = datetime_str
            records.append(record_copy)
        
        # DataFrame oluştur
        self.df = pd.DataFrame(records)
        
        # Datetime sütununu datetime tipine çevir
        self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        self.df.set_index('datetime', inplace=True)
        
        print(f"📊 DataFrame oluşturuldu: {len(self.df)} satır x {len(self.df.columns)} sütun")
        return True
    
    def show_statistics(self):
        """Veri istatistiklerini göster"""
        if self.df is None:
            print("❌ DataFrame bulunamadı!")
            return
        
        print("📈 VERİ İSTATİSTİKLERİ")
        print("=" * 50)
        
        # Numerik sütunları bul
        numeric_cols = ['ERPM', 'RPM', 'Speed', 'Current', 'Duty', 'Voltage', 'Power']
        existing_cols = [col for col in numeric_cols if col in self.df.columns]
        
        for col in existing_cols:
            data = self.df[col].dropna()  # None değerleri çıkar
            if len(data) > 0:
                print(f"\n{col}:")
                print(f"  • Ortalama: {data.mean():.2f}")
                print(f"  • Minimum: {data.min():.2f}")
                print(f"  • Maksimum: {data.max():.2f}")
                print(f"  • Standart Sapma: {data.std():.2f}")
                print(f"  • Veri Sayısı: {len(data)}")
    
    def plot_data(self, save_plot=False):
        """Verileri grafikle"""
        if self.df is None:
            print("❌ DataFrame bulunamadı!")
            return
        
        # Grafik için hazırlık
        numeric_cols = ['ERPM', 'RPM', 'Speed', 'Current', 'Duty', 'Voltage', 'Power']
        existing_cols = [col for col in numeric_cols if col in self.df.columns]
        
        if not existing_cols:
            print("❌ Grafiklenecek veri bulunamadı!")
            return
        
        # Subplot sayısını hesapla
        n_plots = len(existing_cols)
        cols = 2
        rows = (n_plots + 1) // 2
        
        plt.figure(figsize=(15, 4 * rows))
        plt.suptitle(f'Telemetri Verisi Analizi - {self.json_file}', fontsize=16)
        
        for i, col in enumerate(existing_cols):
            plt.subplot(rows, cols, i + 1)
            data = self.df[col].dropna()
            
            if len(data) > 0:
                plt.plot(data.index, data.values, marker='o', markersize=2, linewidth=1)
                plt.title(f'{col}')
                plt.xlabel('Zaman')
                plt.ylabel(col)
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        if save_plot:
            plot_filename = self.json_file.replace('.json', '_analysis.png')
            plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
            print(f"📊 Grafik kaydedildi: {plot_filename}")
        
        try:
            plt.show()
        except:
            print("📊 Grafik gösterimi başarısız (GUI olmayabilir)")
    
    def export_summary(self):
        """Özet rapor oluştur"""
        if self.df is None:
            print("❌ DataFrame bulunamadı!")
            return
        
        summary_filename = self.json_file.replace('.json', '_summary.txt')
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write("TELEMETRI VERİSİ ÖZET RAPORU\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Dosya: {self.json_file}\n")
            f.write(f"Analiz Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Toplam Kayıt: {len(self.df)}\n\n")
            
            # İstatistikler
            numeric_cols = ['ERPM', 'RPM', 'Speed', 'Current', 'Duty', 'Voltage', 'Power']
            existing_cols = [col for col in numeric_cols if col in self.df.columns]
            
            for col in existing_cols:
                data = self.df[col].dropna()
                if len(data) > 0:
                    f.write(f"{col}:\n")
                    f.write(f"  Ortalama: {data.mean():.2f}\n")
                    f.write(f"  Minimum: {data.min():.2f}\n")
                    f.write(f"  Maksimum: {data.max():.2f}\n")
                    f.write(f"  Standart Sapma: {data.std():.2f}\n")
                    f.write(f"  Veri Sayısı: {len(data)}\n\n")
        
        print(f"📄 Özet rapor oluşturuldu: {summary_filename}")

def main():
    if len(sys.argv) != 2:
        print("Kullanım: python analyze_telemetry.py <json_dosyasi>")
        print("Örnek: python analyze_telemetry.py telemetri_data_20250930_215719.json")
        return
    
    json_file = sys.argv[1]
    
    print("🔍 Telemetri JSON Analiz Aracı")
    print("=" * 40)
    print()
    
    analyzer = TelemetryAnalyzer(json_file)
    
    # Veriyi yükle
    if not analyzer.load_data():
        return
    
    # DataFrame'e dönüştür
    if not analyzer.convert_to_dataframe():
        return
    
    # Analizleri yap
    analyzer.show_statistics()
    print()
    
    # Kullanıcıya seçenek sun
    print("Seçenekler:")
    print("1. Grafik göster")
    print("2. Grafik göster ve kaydet")
    print("3. Özet rapor oluştur")
    print("4. Hepsini yap")
    print("5. Çıkış")
    
    try:
        choice = input("\nSeçiminizi yapın (1-5): ").strip()
        
        if choice == '1':
            analyzer.plot_data()
        elif choice == '2':
            analyzer.plot_data(save_plot=True)
        elif choice == '3':
            analyzer.export_summary()
        elif choice == '4':
            analyzer.plot_data(save_plot=True)
            analyzer.export_summary()
        elif choice == '5':
            print("👋 Çıkılıyor...")
        else:
            print("❌ Geçersiz seçim!")
            
    except KeyboardInterrupt:
        print("\n👋 Çıkılıyor...")

if __name__ == '__main__':
    main()