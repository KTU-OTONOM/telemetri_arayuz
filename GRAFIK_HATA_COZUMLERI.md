# Grafik Kaydetme Hata Çözümleri

## Sorun: `module 'pyqtgraph' has no attribute 'exporters'`

Bu hata PyQtGraph'ın exporters modülünün düzgün yüklenmemesinden kaynaklanır.

### Çözüm 1: PyQtGraph Güncellemesi (Önerilen)

```bash
pip uninstall pyqtgraph
pip install pyqtgraph --upgrade
```

### Çözüm 2: Requirements'tan Yeniden Kurulum

```bash
pip install -r requirements.txt --force-reinstall
```

### Çözüm 3: Matplotlib Kullanımı

Eğer PyQtGraph exporters hala çalışmıyorsa, uygulama otomatik olarak matplotlib'e geçecek:

```bash
pip install matplotlib
```

### Çözüm 4: Manuel Test

Test script'ini çalıştırarak sorunu teşhis edin:

```bash
python test_exporters.py
```

## Alternatif Grafik Kaydetme Yöntemleri

Uygulama şu sırayla kaydetme yöntemlerini dener:

### 1. PyQtGraph ImageExporter (Birincil)
- En yüksek kalite
- Vektörel çıktı desteği
- PDF kaydetme

### 2. QPixmap Screenshot (İkincil)
- Widget'tan direkt screenshot
- Hızlı ve güvenilir
- PNG/JPG çıktı

### 3. Matplotlib (Üçüncül)
- Ham veriden grafik yeniden çizimi
- Özelleştirilebilir stil
- Professional görünüm

## Hata Çözümü Kontrol Listesi

### ✅ Kontrol Edilecekler:

1. **PyQtGraph versiyonu:**
   ```bash
   python -c "import pyqtgraph; print(pyqtgraph.__version__)"
   ```

2. **Exporters modülü:**
   ```bash
   python -c "import pyqtgraph.exporters; print('OK')"
   ```

3. **Matplotlib kurulu mu:**
   ```bash
   python -c "import matplotlib; print('OK')"
   ```

4. **Qt backend:**
   ```bash
   python -c "import PyQt5; print('PyQt5 OK')"
   ```

### 🔧 Muhtemel Sorunlar:

1. **Eski PyQtGraph versiyonu**
   - Çözüm: `pip install --upgrade pyqtgraph`

2. **Eksik bağımlılıklar**
   - Çözüm: `pip install -r requirements.txt`

3. **Virtual environment sorunu**
   - Çözüm: Venv'i yeniden aktifleştir

4. **Sistem Python karışıklığı**
   - Çözüm: `python -m pip install pyqtgraph`

## Test Komutu

```bash
cd "d:\KATOT\telemetri_arayuz"
python test_exporters.py
```

Bu komut tüm grafik kaydetme yöntemlerini test eder ve sorunu teşhis eder.

## Başarılı Kurulum Doğrulaması

Grafik kaydetme özelliği çalışıyorsa:

1. ✅ Ana uygulamada "📸 Tüm Grafikleri Kaydet" butonu çalışır
2. ✅ Her grafiğe sağ tıklayarak kaydetme menüsü açılır
3. ✅ Log panelinden seçerek grafik kaydedilir
4. ✅ PNG/JPG dosyaları oluşturulur

## İletişim

Sorun devam ederse:
1. `test_exporters.py` çıktısını kaydedin
2. Hata mesajının tam metnini not alın
3. PyQtGraph versiyonunu kontrol edin