# Mesafe Hesaplama Aracı

JSON telemetri dosyalarından zaman ve hız verilerini kullanarak toplam kat edilen mesafeyi hesaplar.

## Kullanım

### Komut Satırı

```bash
python calculate_distance.py [json_dosyasi]
```

### Batch Dosyası (Windows)

```bash
calculate_distance.bat [json_dosyasi]
```

### Örnekler

```bash
# Varsayılan dosya
python calculate_distance.py

# Belirli bir dosya
python calculate_distance.py 2025_yarisma_verileri_1_FIXED.json

# Batch ile
calculate_distance.bat 2025_yarisma_verileri_1_FIXED.json
```

## Hesaplama Yöntemi

Mesafe hesaplama formülü:

```
Mesafe (km) = Ortalama Hız (km/h) × Zaman Farkı (saniye) / 3600
```

Her iki ardışık kayıt arasında:
1. Zaman farkı hesaplanır (saniye)
2. Ortalama hız hesaplanır: `(önceki_hız + şimdiki_hız) / 2`
3. Mesafe artışı: `ortalama_hız × zaman_farkı / 3600`
4. Toplam mesafeye eklenir

## Çıktı

### Konsol Çıktısı

```
🚗 TELEMETRI MESAFE HESAPLAYICI v1.0
============================================================

📂 Dosya okunuyor: 2025_yarisma_verileri_1_FIXED.json
============================================================
📅 Export Zamanı: 2025-10-08T09:12:42.410004
📊 Toplam Kayıt: 3671
📈 Veri Tipleri: Speed, Current, Voltage, Power, ERPM, RPM, Duty

✅ 3671 adet zaman-hız verisi bulundu

🔄 Mesafe hesaplanıyor...
------------------------------------------------------------
  ⏳ İlerleme: 13.6% (500/3671)
  ⏳ İlerleme: 27.2% (1000/3671)
  ...

============================================================
📊 MESAFE HESAPLAMA SONUÇLARI
============================================================

🕐 Başlangıç Zamanı: 2025-10-05 14:19:12
🕐 Bitiş Zamanı:     2025-10-05 14:54:54
⏱️  Toplam Süre:      0.59 saat (35.70 dakika)

🛣️  TOPLAM MESAFE:    14.515 km
                     14514.6 metre

➡️  İleri Mesafe:     14.515 km
⬅️  Geri Mesafe:      0.000 km
⏸️  Durma Sayısı:     24 kayıt

🚀 Maksimum Hız:     30.96 km/h
📊 Ortalama Hız:     24.41 km/h

============================================================
💾 Özet dosya kaydedildi: 2025_yarisma_verileri_1_FIXED_distance_summary.json

✅ Hesaplama tamamlandı!
```

### Özet JSON Dosyası

Otomatik olarak `[dosya_adı]_distance_summary.json` dosyası oluşturulur:

```json
{
  "calculation_info": {
    "source_file": "2025_yarisma_verileri_1_FIXED.json",
    "calculation_time": "2025-10-18T14:41:54.452498",
    "total_records": 3671
  },
  "time_info": {
    "start_time": "2025-10-05T14:19:12.823000",
    "end_time": "2025-10-05T14:54:54.791000",
    "duration_seconds": 2141.968,
    "duration_minutes": 35.699,
    "duration_hours": 0.595
  },
  "distance_info": {
    "total_distance_km": 14.515,
    "total_distance_meters": 14514.6,
    "forward_distance_km": 14.515,
    "backward_distance_km": 0.000
  },
  "speed_info": {
    "max_speed_kmh": 30.96,
    "average_speed_kmh": 24.41,
    "zero_speed_count": 24
  }
}
```

## İstatistikler

Araç aşağıdaki istatistikleri hesaplar:

**Zaman Bilgileri:**
- Başlangıç ve bitiş zamanları
- Toplam süre (saniye, dakika, saat)

**Mesafe Bilgileri:**
- Toplam mesafe (km ve metre)
- İleri mesafe
- Geri mesafe
- Net mesafe

**Hız Bilgileri:**
- Maksimum hız
- Ortalama hız
- Durma sayısı (hız = 0 olan kayıtlar)

**Hidrojen Verimliliği (varsa):**
- Hidrojen tüketimi (L ve m³)
- Verimlilik (km/m³)

## Özellikler

- ✅ Otomatik ilerleme göstergesi
- ✅ Detaylı hata yönetimi
- ✅ JSON özet dosyası oluşturma
- ✅ İleri ve geri mesafe ayrımı
- ✅ Hidrojen verimlilik hesaplama desteği
- ✅ Türkçe çıktı ve emoji desteği

## Gereksinimler

- Python 3.7+
- JSON formatındaki telemetri dosyası
- Dosyada `Speed` ve `timestamp` verileri bulunmalı

## JSON Format Gereksinimleri

Beklenen JSON formatı:

```json
{
  "export_info": {
    "export_time": "2025-10-08T09:12:42.410004",
    "total_records": 3671,
    "data_types": ["Speed", "Current", "Voltage", ...],
    "format": "datetime_keyed"
  },
  "data": {
    "2025-10-05T11:19:12.823000": {
      "timestamp": 1759663152.823,
      "datetime": "2025-10-05T11:19:12.823000",
      "Speed": 0.0,
      ...
    },
    ...
  }
}
```

## Örnek Sonuç

2025 yarışma verileri için:

- **Toplam Mesafe:** 14.515 km (14,514.6 metre)
- **Toplam Süre:** 35.7 dakika (0.59 saat)
- **Ortalama Hız:** 24.41 km/h
- **Maksimum Hız:** 30.96 km/h
- **Kayıt Sayısı:** 3,671 veri noktası

## Notlar

- Negatif hızlar (geri gidiş) ayrı hesaplanır
- Sıfır hız kayıtları istatistiklere dahildir
- Zaman damgaları Unix timestamp formatında olmalıdır
- Hız değerleri km/h cinsinden olmalıdır

## Lisans

Bu araç, Arduino Telemetri Arayüzü projesinin bir parçasıdır.
