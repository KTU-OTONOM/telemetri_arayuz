#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQtGraph Exporters Test Script
PyQtGraph exporters modülünün çalışıp çalışmadığını test eder
"""

def test_pyqtgraph_exporters():
    """PyQtGraph exporters test et"""
    print("🔍 PyQtGraph Exporters Test")
    print("=" * 40)
    
    try:
        import pyqtgraph as pg
        print("✅ PyQtGraph import edildi")
        
        # Exporters modülünü test et
        try:
            import pyqtgraph.exporters
            print("✅ pyqtgraph.exporters import edildi")
            
            # ImageExporter'ı test et
            try:
                exporter_class = pyqtgraph.exporters.ImageExporter
                print("✅ ImageExporter sınıfı bulundu")
                print(f"📋 ImageExporter: {exporter_class}")
                
            except AttributeError as e:
                print(f"❌ ImageExporter bulunamadı: {e}")
                
        except ImportError as e:
            print(f"❌ pyqtgraph.exporters import hatası: {e}")
            
        # Alternatif import yöntemini test et
        try:
            from pyqtgraph.exporters import ImageExporter
            print("✅ Alternatif import yöntemi çalışıyor")
            
        except ImportError as e:
            print(f"❌ Alternatif import hatası: {e}")
            
        # Mevcut exporters'ları listele
        try:
            import pyqtgraph.exporters as exporters
            print(f"📋 Mevcut exporters modülü: {dir(exporters)}")
            
        except ImportError:
            print("❌ Exporters modülü bulunamadı")
            
    except ImportError as e:
        print(f"❌ PyQtGraph import hatası: {e}")
        return False
    
    print()
    return True

def test_matplotlib_alternative():
    """Matplotlib alternatif test et"""
    print("🔍 Matplotlib Alternatif Test")
    print("=" * 40)
    
    try:
        import matplotlib.pyplot as plt
        print("✅ Matplotlib import edildi")
        
        # Basit grafik oluştur ve kaydet
        import numpy as np
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        plt.figure(figsize=(8, 6))
        plt.plot(x, y)
        plt.title("Test Grafiği")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.grid(True)
        
        test_filename = "matplotlib_test.png"
        plt.savefig(test_filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Test grafiği kaydedildi: {test_filename}")
        
    except ImportError as e:
        print(f"❌ Matplotlib import hatası: {e}")
        print("💡 Çözüm: pip install matplotlib")
        return False
    except Exception as e:
        print(f"❌ Matplotlib test hatası: {e}")
        return False
    
    print()
    return True

def provide_solutions():
    """Çözüm önerileri"""
    print("💡 ÇÖZÜM ÖNERİLERİ")
    print("=" * 40)
    
    print("1. PyQtGraph Güncellemesi:")
    print("   pip install --upgrade pyqtgraph")
    print()
    
    print("2. PyQtGraph Yeniden Kurulum:")
    print("   pip uninstall pyqtgraph")
    print("   pip install pyqtgraph")
    print()
    
    print("3. Matplotlib Alternatifi (Önerilen):")
    print("   pip install matplotlib")
    print("   Uygulama otomatik olarak matplotlib kullanacak")
    print()
    
    print("4. Tam Gereksinimler:")
    print("   pip install -r requirements.txt --force-reinstall")
    print()

def main():
    print("🔧 Grafik Kaydetme Hata Tanılama Aracı")
    print("=" * 50)
    print()
    
    # PyQtGraph test
    pyqt_ok = test_pyqtgraph_exporters()
    
    # Matplotlib test  
    matplotlib_ok = test_matplotlib_alternative()
    
    # Özet
    print("📊 ÖZET")
    print("=" * 40)
    
    if pyqt_ok:
        print("✅ PyQtGraph: Çalışıyor")
    else:
        print("❌ PyQtGraph: Sorunlu")
    
    if matplotlib_ok:
        print("✅ Matplotlib: Çalışıyor (Alternatif)")
    else:
        print("❌ Matplotlib: Kurulu değil")
    
    print()
    
    # Çözüm önerileri
    if not pyqt_ok or not matplotlib_ok:
        provide_solutions()
    else:
        print("🎉 Tüm grafik kaydetme yöntemleri çalışıyor!")

if __name__ == '__main__':
    main()