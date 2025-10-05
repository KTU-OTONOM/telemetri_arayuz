# Seri Port Tanımlama Kılavuzu

## Port Türleri ve Anlamları

Telemetri arayüzü artık seri portları daha akıllıca tanımlayabilir. İşte port türlerinin anlamları:

### 🔧 Arduino
- **Gerçek Arduino kartları** (Uno, Nano, Mega, vb.)
- **USB üzerinden bağlı Arduino kartları**
- **Arduino IDE tarafından tanınan kartlar**
- **VID/PID değerleri Arduino LLC'ye ait kartlar**

**Önerilen:** Arduino projeleriniz için bu portları seçin.

### 🌐 ESP Board  
- **ESP32 ve ESP8266 kartları**
- **NodeMCU, Wemos D1 gibi ESP tabanlı kartlar**
- **WiFi/Bluetooth özellikli mikrokontrolörler**

**Önerilen:** ESP tabanlı projeleriniz için bu portları seçin.

### 📶 Bluetooth
- **Bluetooth seri adaptörleri**
- **Bluetooth modül bağlantıları**
- **Kablosuz seri iletişim**

**Dikkat:** Bu portları seçtiğinizde uyarı alacaksınız. Arduino'nuz gerçekten Bluetooth modülü ile mi bağlı olduğunu kontrol edin.

### 🔌 USB Serial
- **USB-Serial çevirici kartlar**
- **CH340, CP2102, FTDI çipleri**
- **Genel amaçlı USB-Serial adaptörler**

**Uyumlu:** Çoğu Arduino clone kartı bu kategori altında görünür.

### 📟 Serial
- **Standart seri portlar**
- **RS232 portları**
- **Eski tip seri bağlantılar**

### ❓ Diğer
- **Tanımlanamayan portlar**
- **Sürücüsü eksik cihazlar**
- **Bilinmeyen USB cihazları**

## Hangi Portu Seçmeliyim?

### Arduino Projeleri İçin:
1. **İlk tercih:** 🔧 Arduino portları
2. **İkinci tercih:** 🔌 USB Serial portları
3. **Üçüncü tercih:** 🌐 ESP Board (ESP kartları için)

### Bluetooth Bağlantısı:
- Sadece Arduino'nuz HC-05, HC-06 gibi Bluetooth modülü ile bağlıysa 📶 Bluetooth portunu seçin
- Aksi takdirde USB kablosu ile bağlı Arduino için Bluetooth portunu seçmeyin

### Problem Giderme:

#### Port Görünmüyor
1. **USB kablosunu** kontrol edin
2. **Arduino IDE'de** port görünüyor mu kontrol edin
3. **"Portları Yenile"** butonuna basın
4. **Sürücülerin** kurulu olduğundan emin olun

#### Bağlantı Hatası
1. **Doğru portu** seçtiğinizden emin olun
2. **Baud rate'i** kontrol edin (genelde 9600)
3. **Arduino Serial Monitor'u** kapatın (aynı anda iki program port kullanamaz)
4. **Başka program** portu kullanıyor olabilir

#### Yanlış Port Seçimi
- Bluetooth port seçtiyseniz uyarı mesajı alacaksınız
- Emin değilseniz "Hayır" seçin ve doğru portu bulun
- Arduino IDE'de hangi port çalışıyorsa onu seçin

## VID/PID Bilgileri

Uygulamada artık VID/PID bilgileri de gösteriliyor:
- **VID (Vendor ID):** Üretici kimliği
- **PID (Product ID):** Ürün kimliği

Örnek: `[VID:PID=2341:0043]` → Arduino Uno

### Bilinen Arduino VID/PID'ler:
- `2341:0043` - Arduino Uno Rev3
- `2341:0001` - Arduino Uno Rev1
- `1A86:7523` - CH340 çipli Arduino cloneları
- `10C4:EA60` - CP210x çipli kartlar

Bu bilgiler portun gerçek kimliğini anlamanıza yardımcı olur.