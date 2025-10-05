# Arduino Telemetri Arayüzü

Arduino'dan gelen telemetri verilerini gerçek zamanlı olarak görüntüleyen, grafikleyen ve kaydeden PyQt5 tabanlı masaüstü uygulaması.

## Özellikler

- **Gerçek Zamanlı Veri Görüntüleme**: Arduino'dan gelen telemetri verilerini anlık olarak görüntüler
- **Virtual Arduino Desteği**: Gerçek Arduino olmadan test edebilme imkanı
- **Akıllı Port Tanıma**: Arduino, ESP, Bluetooth ve diğer port türlerini otomatik tanır
- **TCP Socket Desteği**: Virtual Arduino simulatörü ile TCP bağlantısı
- **Grafik Gösterimi**: 6 farklı parametrenin grafiklerini aynı anda gösterir
- **Veri Loglama**: Gelen tüm verileri zaman damgası ile loglar
- **Veri Kaydetme**: CSV ve JSON formatlarında veri kaydetme
- **Seri Port Yönetimi**: Otomatik port tarama ve bağlantı kontrolü
- **Ayarlanabilir Parametreler**: Maksimum veri noktası sayısı, baud rate seçimi

## Desteklenen Telemetri Verileri

- **ERPM**: Elektriksel RPM
- **RPM**: Döner dakika (RPM)
- **Hız**: km/s cinsinden hız
- **Akım**: Amper cinsinden akım
- **Duty**: Duty cycle yüzdesi
- **Gerilim**: Volt cinsinden gerilim
- **Güç**: Watt cinsinden güç

## Kurulum

### Gereksinimler

Python 3.7 veya üzeri gereklidir.

### Paket Kurulumu

```bash
pip install -r requirements.txt
```

veya manuel olarak:

```bash
pip install PyQt5==5.15.9
pip install pyqtgraph==0.13.3
pip install pyserial==3.5
pip install numpy==1.24.3
```

## Kullanım

### Ana Uygulamayı Başlatma

```bash
python main.py
```

### Arduino Simulatörü (Test Amaçlı)

**Virtual Arduino Simulatör (Önerilen):**
```bash
python virtual_arduino.py tcp
```

veya batch dosyası ile:
```bash
run_virtual_arduino.bat
```

**Eski Konsol Simulatörü:**
```bash
python arduino_simulator.py
```

## Virtual Arduino Kullanımı

1. **Virtual Arduino'yu başlatın:**
   ```bash
   python virtual_arduino.py tcp
   ```

2. **Telemetri arayüzünü açın:**
   ```bash
   python main.py
   ```

3. **Port listesinde "🖥️ Virtual Arduino Simulator" seçeneğini seçin**

4. **"Bağlan" butonuna basın**

5. **Veriler otomatik olarak gelmeye başlayacak**

## Arduino Veri Formatı

Uygulama aşağıdaki formatta gelen verileri otomatik olarak parse eder:

```
11:19:12.775 -> ----- ALINAN VERİ -----
11:19:12.823 -> ERPM: -6
11:19:12.823 -> RPM: 0
11:19:12.823 -> Hız (km/s): 0.00
11:19:12.823 -> Akım (A): -0.20
11:19:12.823 -> Duty: 0
11:19:12.823 -> Gerilim (V): 19.47
11:19:12.823 -> Güç (W): -3.89
```

## Kullanıcı Arayüzü

### 1. Bağlantı Kontrolü
- **Seri Port Seçimi**: Mevcut seri portların listesi
- **Baud Rate**: 9600, 19200, 38400, 57600, 115200
- **Bağlan/Kes**: Seri port bağlantısını kontrol eder
- **Portları Yenile**: Mevcut portları yeniden tarar
- **Grafikleri Temizle**: Tüm grafik verilerini siler
- **📸 Tüm Grafikleri Kaydet**: Tüm grafikleri tek dosyada PNG/JPG/PDF olarak kaydet

### 2. Anlık Değerler
Sol panelde tüm telemetri verilerinin anlık değerleri gösterilir.

### 3. Grafikler - Gelişmiş Özellikler
Sağ panelde 6 farklı grafik aynı anda gösterilir:
- Hız (km/s)
- Akım (A)
- Gerilim (V)
- Güç (W)
- RPM
- ERPM

**Grafik Kaydetme Özellikleri:**
- **Sağ Tık Menüsü**: Her grafiğe sağ tıklayarak:
  - 📸 Tek grafik kaydetme
  - 📸 Tüm grafikleri kaydetme
  - 🗑️ Tek grafik temizleme
- **Combobox Seçimi**: Log panelinden istediğiniz grafiği seçip kaydetme
- **Yüksek Çözünürlük**: PNG, JPG ve PDF formatlarında kaydetme
- **Otomatik İsimlendirme**: Tarih-saat damgası ile dosya adları

### 4. Grafik Formatları
- **PNG**: Yüksek kaliteli raster görüntü (önerilen)
- **JPG**: Sıkıştırılmış raster görüntü
- **PDF**: Vektörel format (yazdırma için ideal)
- Akım (A)
- Gerilim (V)
- Güç (W)
- RPM
- ERPM

### 5. Log ve Kaydetme
- **Maksimum Veri Noktası**: Grafiklerde tutulacak maksimum veri sayısı
- **CSV Kaydet**: Verileri CSV formatında kaydeder
- **JSON Kaydet**: Verileri JSON formatında kaydeder
- **Grafik Kaydet Seçimi**: Dropdown menüden istediğiniz grafiği seçerek kaydetme
- **📸 Grafik Kaydet**: Seçilen grafiği yüksek çözünürlükte kaydetme
- **Log Alanı**: Gelen tüm verilerin gerçek zamanlı logu

## Veri Kaydetme Formatları

### CSV Format
```csv
Timestamp,DateTime,ERPM,RPM,Speed,Current,Duty,Voltage,Power
1634567890.123,2021-10-18 14:31:30.123000,-6,0,0.00,-0.20,0,19.47,-3.89
```

### JSON Format
```json
{
  "export_info": {
    "export_time": "2021-10-18T14:31:30.123456",
    "total_records": 3,
    "data_types": ["ERPM", "RPM", "Speed", "Current", "Duty", "Voltage", "Power"],
    "format": "datetime_keyed"
  },
  "data": {
    "2021-10-18T14:31:30.123000": {
      "timestamp": 1634567890.123,
      "datetime": "2021-10-18T14:31:30.123000",
      "ERPM": -6,
      "RPM": 0,
      "Speed": 0.00,
      "Current": -0.20,
      "Duty": 0,
      "Voltage": 19.47,
      "Power": -3.89
    },
    "2021-10-18T14:31:31.234000": {
      "timestamp": 1634567891.234,
      "datetime": "2021-10-18T14:31:31.234000",
      "ERPM": -8,
      "RPM": 0,
      "Speed": 0.00,
      "Current": -0.25,
      "Duty": 0,
      "Voltage": 19.45,
      "Power": -4.86
    }
  }
}
```

## Özelleştirme

### Maksimum Veri Noktası
Grafiklerde gösterilecek maksimum veri noktası sayısını ayarlayabilirsiniz (100-10000 arası).

### Grafik Renkleri
Kod içerisinde `plot_configs` listesinde grafik renklerini değiştirebilirsiniz.

## Sorun Giderme

### Seri Port Bulunamıyor
- Arduino'nun bilgisayara düzgün bağlandığından emin olun
- Arduino IDE'de hangi porta bağlı olduğunu kontrol edin
- "Portları Yenile" butonuna basın

### Veri Gelmiyor
- Baud rate ayarının Arduino ile uyumlu olduğundan emin olun
- Arduino kodunun doğru formatta veri gönderdiğini kontrol edin
- Seri monitörde veri geldiğinden emin olun

### Uygulama Donuyor
- Maksimum veri noktası sayısını azaltın
- Grafikleri temizleyin
- Uygulamayı yeniden başlatın

## Veri Analizi

### JSON Analiz Aracı

Kaydedilmiş JSON dosyalarını analiz etmek için:

```bash
python analyze_telemetry.py telemetri_data_20250930_215719.json
```

veya batch dosyası ile:

```bash
analyze_data.bat telemetri_data_20250930_215719.json
```

**Analiz aracının özellikleri:**
- **İstatistiksel analiz**: Ortalama, minimum, maksimum, standart sapma
- **Grafik görüntüleme**: Tüm parametrelerin zaman serisi grafikleri
- **Grafik kaydetme**: PNG formatında grafik kaydetme
- **Özet rapor**: TXT formatında detaylı rapor oluşturma
- **Pandas DataFrame**: Veriyi pandas ile analiz etme

**Analiz için ek paketler:**
```bash
pip install pandas matplotlib
```

### JSON Dosya Yapısı

Yeni JSON formatında her datetime anahtarının altında o anki tüm telemetri verileri bulunur:

```json
{
  "data": {
    "2025-09-30T21:57:19.123456": {
      "timestamp": 1727733439.123456,
      "datetime": "2025-09-30T21:57:19.123456",
      "ERPM": -6,
      "RPM": 0,
      "Speed": 0.00,
      "Current": -0.20,
      "Duty": 0,
      "Voltage": 19.47,
      "Power": -3.89
    }
  }
}
```

Bu yapı sayesinde:
- Her zaman noktasındaki tüm verilere kolay erişim
- Zaman bazlı sıralama ve filtreleme
- Pandas DataFrame ile kolay analiz
- Eksik veri kontrolü (None değerler)

## Proje Dosyaları

- `main.py` - Ana telemetri arayüzü
- `virtual_arduino.py` - Virtual Arduino simulatörü
- `arduino_simulator.py` - Konsol simulatörü (eski)
- `analyze_telemetry.py` - JSON analiz aracı
- `requirements.txt` - Python paket gereksinimleri
- `PORT_GUIDE.md` - Seri port kullanım kılavuzu
- `*.bat` - Windows batch dosyaları

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## Katkıda Bulunma

1. Projeyi fork edin
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`)
4. Branch'inizi push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## İletişim

Sorularınız için GitHub Issues kullanabilirsiniz.