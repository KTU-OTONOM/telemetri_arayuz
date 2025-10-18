#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arduino Telemetri Arayüzü
Seri port üzerinden Arduino'dan gelen telemetri verilerini görüntüler
"""

import sys

# Python sürüm kontrolü
if sys.version_info < (3, 7):
    print("HATA: Bu uygulama Python 3.7 veya üzeri gerektirir.")
    print(f"Mevcut Python sürümü: {sys.version}")
    print("Lütfen Python'u güncelleyin: https://python.org/downloads/")
    sys.exit(1)

# Paket import kontrolü
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("HATA: pyserial paketi bulunamadı!")
    print("Kurulum için: pip install pyserial")
    sys.exit(1)

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("HATA: PyQt5 paketi bulunamadı!")
    print("Kurulum için: pip install PyQt5")
    sys.exit(1)

import os
import re
import socket
from datetime import datetime
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QTextEdit, QGroupBox, QGridLayout, QMessageBox,
                             QFileDialog, QSpinBox, QDoubleSpinBox, QMenu, QAction, QDialog,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QScrollArea)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QPalette, QPixmap, QPainter, QBrush
import pyqtgraph as pg
import pyqtgraph.exporters

# Arduino tanıma için VID/PID listesi
ARDUINO_VID_PID = {
    '2341': ['0043', '0001', '0042', '0243', '8036', '8037'],  # Arduino LLC
    '1B4F': ['9206', '9207', '9208'],  # SparkFun
    '16C0': ['0483'],  # VOTI (Arduino clones)
    '10C4': ['EA60'],  # Silicon Labs (ESP32 boards)
    '1A86': ['7523'],  # QinHeng Electronics (CH340)
    '0403': ['6001', '6014'],  # FTDI (FTDI chips)
}

def is_arduino_port(port):
    """Portun Arduino olup olmadığını kontrol et"""
    if not hasattr(port, 'vid') or not hasattr(port, 'pid'):
        return False
    
    vid = f"{port.vid:04X}" if port.vid else ""
    pid = f"{port.pid:04X}" if port.pid else ""
    
    return vid in ARDUINO_VID_PID and pid in ARDUINO_VID_PID[vid]

def classify_port(port):
    """Port tipini sınıflandır"""
    description = port.description.lower()
    manufacturer = getattr(port, 'manufacturer', '').lower() if hasattr(port, 'manufacturer') else ''
    
    # Arduino kontrolü
    if (is_arduino_port(port) or 
        'arduino' in description or 
        'arduino' in manufacturer or
        'uno' in description or 
        'nano' in description or
        'mega' in description):
        return "🔧 Arduino", "Arduino"
    
    # ESP32/ESP8266 kontrolü
    elif ('esp32' in description or 'esp8266' in description or
          'nodemcu' in description or 'wemos' in description):
        return "🌐 ESP Board", "ESP"
    
    # Bluetooth kontrolü
    elif ('bluetooth' in description or 'bt' in description.replace(' ', '') or
          'blue' in description):
        return "📶 Bluetooth", "Bluetooth"
    
    # USB Serial kontrolü
    elif ('usb' in description and 'serial' in description) or 'ch340' in description or 'cp210' in description:
        return "🔌 USB Serial", "USB Serial"
    
    # Genel Serial
    elif 'serial' in description or 'com' in description:
        return "📟 Serial", "Serial"
    
    # Bilinmeyen
    else:
        return "❓ Diğer", "Unknown"

class TCPThread(QThread):
    """TCP socket bağlantısı için thread"""
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.is_running = False
        self.socket = None
        
    def run(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_running = True
            
            buffer = ""
            while self.is_running:
                try:
                    data = self.socket.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        break
                        
                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            self.parse_data(line.strip())
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    self.error_occurred.emit(f"TCP okuma hatası: {str(e)}")
                    break
                        
        except Exception as e:
            self.error_occurred.emit(f"TCP bağlantı hatası: {str(e)}")
        finally:
            if self.socket:
                self.socket.close()
    
    def parse_data(self, line):
        """TCP'den gelen veriyi parse et"""
        try:
            # Zaman damgası ve veri kısmını ayır
            if "->" in line:
                parts = line.split("->", 1)
                if len(parts) == 2:
                    timestamp = parts[0].strip()
                    data_part = parts[1].strip()
                    
                    # Veri tipini kontrol et
                    if "ERPM:" in data_part:
                        match = re.search(r'ERPM:\s*(-?\d+)', data_part)
                        if match:
                            erpm = int(match.group(1))
                            self.emit_data("ERPM", erpm, timestamp)
                    elif "RPM:" in data_part:
                        match = re.search(r'RPM:\s*(-?\d+)', data_part)
                        if match:
                            rpm = int(match.group(1))
                            self.emit_data("RPM", rpm, timestamp)
                    elif "Hız" in data_part:
                        match = re.search(r'Hız.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            speed = float(match.group(1))
                            self.emit_data("Speed", speed, timestamp)
                    elif "Akım" in data_part:
                        match = re.search(r'Akım.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            current = float(match.group(1))
                            self.emit_data("Current", current, timestamp)
                    elif "Duty:" in data_part:
                        match = re.search(r'Duty:\s*(-?\d+)', data_part)
                        if match:
                            duty = int(match.group(1))
                            self.emit_data("Duty", duty, timestamp)
                    elif "Gerilim" in data_part:
                        match = re.search(r'Gerilim.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            voltage = float(match.group(1))
                            self.emit_data("Voltage", voltage, timestamp)
                    elif "Güç" in data_part:
                        match = re.search(r'Güç.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            power = float(match.group(1))
                            self.emit_data("Power", power, timestamp)
        except Exception as e:
            # Parsing hatalarını logla
            print(f"TCP Parse hatası: {e}, line: {line}")
    
    def emit_data(self, data_type, value, timestamp):
        """Veriyi ana thread'e gönder"""
        data = {
            'type': data_type,
            'value': value,
            'timestamp': timestamp,
            'datetime': datetime.now()
        }
        self.data_received.emit(data)
    
    def stop(self):
        """Thread'i durdur"""
        self.is_running = False
        if self.socket:
            self.socket.close()

class SerialThread(QThread):
    """Seri port okuma thread'i"""
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = False
        self.serial_connection = None
        
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_running = True
            
            buffer = ""
            while self.is_running:
                try:
                    if self.serial_connection.in_waiting > 0:
                        data = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                        buffer += data
                        
                        # Satır satır işle
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                self.parse_data(line)
                    else:
                        # Biraz bekle
                        self.msleep(10)
                        
                except Exception as e:
                    self.error_occurred.emit(f"Seri port okuma hatası: {str(e)}")
                    break
                        
        except Exception as e:
            self.error_occurred.emit(f"Seri port bağlantı hatası: {str(e)}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
    
    def parse_data(self, line):
        """Arduino'dan gelen veriyi parse et"""
        try:
            # Debug için tüm gelen veriyi yazdır
            print(f"Seri port verisi: {line}")
            
            # Zaman damgası ve veri kısmını ayır
            if "->" in line:
                parts = line.split("->", 1)
                if len(parts) == 2:
                    timestamp = parts[0].strip()
                    data_part = parts[1].strip()
                    
                    # Veri tipini kontrol et
                    if "ERPM:" in data_part:
                        match = re.search(r'ERPM:\s*(-?\d+)', data_part)
                        if match:
                            erpm = int(match.group(1))
                            self.emit_data("ERPM", erpm, timestamp)
                    elif "RPM:" in data_part:
                        match = re.search(r'RPM:\s*(-?\d+)', data_part)
                        if match:
                            rpm = int(match.group(1))
                            self.emit_data("RPM", rpm, timestamp)
                    elif "Hız" in data_part:
                        match = re.search(r'Hız.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            speed = float(match.group(1))
                            self.emit_data("Speed", speed, timestamp)
                    elif "Akım" in data_part:
                        match = re.search(r'Akım.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            current = float(match.group(1))
                            self.emit_data("Current", current, timestamp)
                    elif "Duty:" in data_part:
                        match = re.search(r'Duty:\s*(-?\d+)', data_part)
                        if match:
                            duty = int(match.group(1))
                            self.emit_data("Duty", duty, timestamp)
                    elif "Gerilim" in data_part:
                        match = re.search(r'Gerilim.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            voltage = float(match.group(1))
                            self.emit_data("Voltage", voltage, timestamp)
                    elif "Güç" in data_part:
                        match = re.search(r'Güç.*?:\s*(-?\d+\.?\d*)', data_part)
                        if match:
                            power = float(match.group(1))
                            self.emit_data("Power", power, timestamp)
            else:
                # Arduino'nun direkt veri göndermesi durumu (format olmadan)
                # Örnek: ERPM:-6 RPM:0 Hız:0.00 Akım:-0.20 Duty:0 Gerilim:19.47 Güç:-3.89
                # Bu durumu da kontrol et
                if any(keyword in line for keyword in ["ERPM", "RPM", "Hız", "Akım", "Duty", "Gerilim", "Güç"]):
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    # Her parametreyi ayrı ayrı parse et
                    erpm_match = re.search(r'ERPM:\s*(-?\d+)', line)
                    if erpm_match:
                        self.emit_data("ERPM", int(erpm_match.group(1)), timestamp)
                    
                    rpm_match = re.search(r'RPM:\s*(-?\d+)', line)
                    if rpm_match:
                        self.emit_data("RPM", int(rpm_match.group(1)), timestamp)
                    
                    speed_match = re.search(r'Hız.*?:\s*(-?\d+\.?\d*)', line)
                    if speed_match:
                        self.emit_data("Speed", float(speed_match.group(1)), timestamp)
                    
                    current_match = re.search(r'Akım.*?:\s*(-?\d+\.?\d*)', line)
                    if current_match:
                        self.emit_data("Current", float(current_match.group(1)), timestamp)
                    
                    duty_match = re.search(r'Duty:\s*(-?\d+)', line)
                    if duty_match:
                        self.emit_data("Duty", int(duty_match.group(1)), timestamp)
                    
                    voltage_match = re.search(r'Gerilim.*?:\s*(-?\d+\.?\d*)', line)
                    if voltage_match:
                        self.emit_data("Voltage", float(voltage_match.group(1)), timestamp)
                    
                    power_match = re.search(r'Güç.*?:\s*(-?\d+\.?\d*)', line)
                    if power_match:
                        self.emit_data("Power", float(power_match.group(1)), timestamp)
                        
        except Exception as e:
            # Parsing hatalarını logla
            print(f"Seri Parse hatası: {e}, line: {line}")
    
    def emit_data(self, data_type, value, timestamp):
        """Veriyi ana thread'e gönder"""
        data = {
            'type': data_type,
            'value': value,
            'timestamp': timestamp,
            'datetime': datetime.now()
        }
        self.data_received.emit(data)
    
    def stop(self):
        """Thread'i durdur"""
        self.is_running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

class SpeedDisplayWidget(QWidget):
    """Hız gösterimi için özel widget"""
    def __init__(self):
        super().__init__()
        self.speed_value = 0.0
        self.speed_frame_path = os.path.join('images', 'hiz.png')
        self.setFixedSize(400, 280)  # Çerçeve küçültüldü
        
    def set_speed(self, speed):
        """Hız değerini güncelle"""
        self.speed_value = speed
        self.update()
    
    def paintEvent(self, event):
        """Widget'ı çiz"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Çerçeve resmini çiz
        if os.path.exists(self.speed_frame_path):
            frame_pixmap = QPixmap(self.speed_frame_path)
            if not frame_pixmap.isNull():
                # Resmi widget boyutuna ölçekle
                scaled_pixmap = frame_pixmap.scaled(
                    self.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                # Resmi ortala
                x_offset = (self.width() - scaled_pixmap.width()) // 2
                y_offset = (self.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        
        # Hız değerini çiz
        font = QFont()
        font.setPointSize(36)  # Font boyutu küçültüldü
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        
        # Metni çiz (daha iyi konumlandırma)
        speed_text = f"{self.speed_value:.1f}"
        text_rect = self.rect()
        # Yeni pozisyon - 150 piksel sağa kaydırıldı (130 + 20)
        text_rect.setLeft(text_rect.left() + 150)  # 130'dan 150'ye çıkarıldı (20 piksel daha sağa)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, speed_text)
        
        # Birim metni kaldırıldı

class DataAnalysisDialog(QDialog):
    """Veri analizi penceresi"""
    def __init__(self, telemetry_data, parent=None):
        super().__init__(parent)
        self.telemetry_data = telemetry_data
        self.setWindowTitle("📊 Telemetri Veri Analizi")
        self.setGeometry(200, 200, 1000, 700)
        self.init_ui()
        self.calculate_statistics()
        
    def init_ui(self):
        """Analiz penceresini oluştur"""
        layout = QVBoxLayout(self)
        
        # Tab widget oluştur
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # İstatistikler sekmesi
        self.create_statistics_tab()
        
        # Grafik sekmesi
        self.create_chart_tab()
        
        # Özet sekmesi
        self.create_summary_tab()
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("📄 Rapor Kaydet")
        export_btn.clicked.connect(self.export_analysis_report)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
    def create_statistics_tab(self):
        """İstatistikler sekmesi"""
        stats_widget = QWidget()
        layout = QVBoxLayout(stats_widget)
        
        # Tablo oluştur
        self.stats_table = QTableWidget()
        layout.addWidget(self.stats_table)
        
        self.tab_widget.addTab(stats_widget, "📈 İstatistikler")
        
    def create_chart_tab(self):
        """Grafik sekmesi"""
        chart_widget = QWidget()
        layout = QVBoxLayout(chart_widget)
        
        # Matplotlib grafikleri için widget
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            
            self.figure = Figure(figsize=(12, 8))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            # Grafik çizme butonu
            plot_btn = QPushButton("🔄 Grafikleri Yenile")
            plot_btn.clicked.connect(self.plot_analysis_charts)
            layout.addWidget(plot_btn)
            
        except ImportError:
            error_label = QLabel("Matplotlib kütüphanesi bulunamadı!\nGrafik görüntüleme için matplotlib gereklidir.")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            layout.addWidget(error_label)
        
        self.tab_widget.addTab(chart_widget, "📊 Grafikler")
        
    def create_summary_tab(self):
        """Özet sekmesi"""
        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        self.tab_widget.addTab(summary_widget, "📋 Özet")
        
    def calculate_statistics(self):
        """İstatistikleri hesapla ve tabloya ekle"""
        # Tablo başlıklarını ayarla
        headers = ['Veri Tipi', 'Ortalama', 'Minimum', 'Maksimum', 'Std. Sapma', 'Veri Sayısı']
        self.stats_table.setColumnCount(len(headers))
        self.stats_table.setHorizontalHeaderLabels(headers)
        
        # Analiz edilecek veri tipleri
        data_types = ['Speed', 'Current', 'Voltage', 'Power', 'RPM', 'ERPM', 'Duty']
        valid_data = []
        
        for data_type in data_types:
            if (data_type in self.telemetry_data and 
                self.telemetry_data[data_type]['values']):
                
                values = self.telemetry_data[data_type]['values']
                if values:
                    import numpy as np
                    stats = {
                        'type': data_type,
                        'mean': np.mean(values),
                        'min': np.min(values),
                        'max': np.max(values),
                        'std': np.std(values),
                        'count': len(values)
                    }
                    valid_data.append(stats)
        
        # Tabloyu doldur
        self.stats_table.setRowCount(len(valid_data))
        
        for row, stats in enumerate(valid_data):
            self.stats_table.setItem(row, 0, QTableWidgetItem(stats['type']))
            self.stats_table.setItem(row, 1, QTableWidgetItem(f"{stats['mean']:.2f}"))
            self.stats_table.setItem(row, 2, QTableWidgetItem(f"{stats['min']:.2f}"))
            self.stats_table.setItem(row, 3, QTableWidgetItem(f"{stats['max']:.2f}"))
            self.stats_table.setItem(row, 4, QTableWidgetItem(f"{stats['std']:.2f}"))
            self.stats_table.setItem(row, 5, QTableWidgetItem(str(stats['count'])))
        
        # Sütun genişliklerini ayarla
        self.stats_table.resizeColumnsToContents()
        
        # Özet metnini oluştur
        self.generate_summary_text(valid_data)
    
    def generate_summary_text(self, stats_data):
        """Özet metni oluştur"""
        summary = "TELEMETRI VERİSİ ANALİZ RAPORU\n"
        summary += "=" * 50 + "\n\n"
        
        total_records = sum(stats['count'] for stats in stats_data)
        summary += f"📊 Toplam Veri Noktası: {total_records}\n"
        summary += f"📈 Analiz Edilen Parametreler: {len(stats_data)}\n"
        summary += f"📅 Analiz Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        summary += "DETAYLI İSTATİSTİKLER:\n"
        summary += "-" * 30 + "\n\n"
        
        for stats in stats_data:
            summary += f"{stats['type']}:\n"
            summary += f"  • Ortalama: {stats['mean']:.2f}\n"
            summary += f"  • Minimum: {stats['min']:.2f}\n"
            summary += f"  • Maksimum: {stats['max']:.2f}\n"
            summary += f"  • Standart Sapma: {stats['std']:.2f}\n"
            summary += f"  • Veri Sayısı: {stats['count']}\n\n"
        
        # Öne çıkan bulgular
        summary += "ÖNE ÇIKAN BULGULAR:\n"
        summary += "-" * 20 + "\n"
        
        for stats in stats_data:
            if stats['type'] == 'Speed' and stats['max'] > 0:
                summary += f"🏎️ Maksimum Hız: {stats['max']:.1f}\n"
            elif stats['type'] == 'Current' and stats['max'] > 0:
                summary += f"⚡ Maksimum Akım: {stats['max']:.1f} A\n"
            elif stats['type'] == 'Power' and stats['max'] > 0:
                summary += f"🔋 Maksimum Güç: {stats['max']:.1f} W\n"
        
        self.summary_text.setText(summary)
    
    def plot_analysis_charts(self):
        """Analiz grafiklerini çiz"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            self.figure.clear()
            
            # Grafik verileri hazırla
            data_types = ['Speed', 'Current', 'Voltage', 'Power']
            available_data = []
            
            for data_type in data_types:
                if (data_type in self.telemetry_data and 
                    self.telemetry_data[data_type]['values'] and
                    self.telemetry_data[data_type]['times']):
                    available_data.append(data_type)
            
            if not available_data:
                # Veri yoksa mesaj göster
                ax = self.figure.add_subplot(1, 1, 1)
                ax.text(0.5, 0.5, 'Grafik çizilecek veri bulunamadı!', 
                       horizontalalignment='center', verticalalignment='center',
                       fontsize=16, transform=ax.transAxes)
                self.canvas.draw()
                return
            
            # Subplot düzenini hesapla
            n_plots = len(available_data)
            if n_plots == 1:
                rows, cols = 1, 1
            elif n_plots == 2:
                rows, cols = 1, 2
            elif n_plots <= 4:
                rows, cols = 2, 2
            else:
                rows, cols = 3, 2
            
            # Her veri tipi için grafik çiz
            for i, data_type in enumerate(available_data):
                ax = self.figure.add_subplot(rows, cols, i + 1)
                
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times:
                    # Relative time'a çevir
                    relative_times = [(t - times[0]) for t in times]
                    ax.plot(relative_times, values, 'o-', markersize=2, linewidth=1)
                
                ax.set_title(f'{data_type}')
                ax.set_xlabel('Zaman (saniye)')
                ax.grid(True, alpha=0.3)
                ax.tick_params(axis='x', rotation=45)
            
            self.figure.suptitle('Telemetri Veri Analizi', fontsize=16, fontweight='bold')
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Grafik çizim hatası:\n{str(e)}")
    
    def export_analysis_report(self):
        """Analiz raporunu kaydet"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Analiz Raporu Kaydet",
            f"telemetri_analiz_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.summary_text.toPlainText())
                
                QMessageBox.information(self, "Başarılı", f"Analiz raporu kaydedildi:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Rapor kaydetme hatası:\n{str(e)}")

class TelemetryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arduino Telemetri Arayüzü")
        self.setGeometry(100, 100, 1400, 900)
        
        # Önce değişkenleri tanımla
        self.max_data_points = 1000
        self.serial_thread = None
        self.start_time = None
        
        # Mesafe takibi için değişkenler
        self.total_distance = 0.0  # km cinsinden
        self.last_speed_time = None
        
        # Hidrojen tüketimi için değişkenler
        self.hydrogen_consumed_liters = 0.0  # Litre cinsinden
        self.hydrogen_efficiency = 0.0  # km/m³
        
        # Veri depolama - sadece ihtiyaç duyulan veriler
        self.telemetry_data = {
            'Speed': {'values': [], 'times': []},
            'Current': {'values': [], 'times': []},
            'Voltage': {'values': [], 'times': []},
            'Power': {'values': [], 'times': []},
            'Distance': {'values': [], 'times': []},  # Yeni: Mesafe verisi
            # Diğer veriler de parse edilecek ama grafik gösterilmeyecek
            'ERPM': {'values': [], 'times': []},
            'RPM': {'values': [], 'times': []},
            'Duty': {'values': [], 'times': []}
        }
        
        self.init_ui()
        self.update_port_list()
        self.set_background_image()  # Koyu temayı ayarla
    
    def set_background_image(self):
        """Koyu tema ayarla"""
        # Sadece dark mode
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 8px;
                font-weight: bold;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #505050;
                border: 2px solid #666666;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #606060;
                border-color: #777777;
            }
            QPushButton:checked {
                background-color: #0078d4;
                border-color: #005a9e;
            }
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                border: 0px;
            }
            QSpinBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        # Grafik arkaplan rengini koyu yap
        if hasattr(self, 'graph_widget'):
            self.graph_widget.setBackground('#2b2b2b')
    
    def init_ui(self):
        """Kullanıcı arayüzünü oluştur"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Üst kontrol paneli
        self.create_control_panel(main_layout)
        
        # Orta kısım - Hız gösterimi, grafikler ve değerler
        middle_layout = QHBoxLayout()
        
        # Sol üst - Hız gösterimi
        speed_layout = QVBoxLayout()
        self.speed_display = SpeedDisplayWidget()
        speed_layout.addWidget(self.speed_display)
        
        # Sol alt - Anlık değerler (sadece ana parametreler)
        self.create_values_panel(speed_layout)
        
        middle_layout.addLayout(speed_layout)
        
        # Sağ kısım - Grafikler (sadece 4 grafik)
        self.create_graphs_panel(middle_layout)
        
        main_layout.addLayout(middle_layout)
        
        # Alt kısım - Log ve kaydetme
        self.create_log_panel(main_layout)
        
    def create_control_panel(self, parent_layout):
        """Kontrol panelini oluştur"""
        control_group = QGroupBox("Bağlantı Kontrolü")
        control_layout = QHBoxLayout(control_group)
        
        # Seri port seçimi
        control_layout.addWidget(QLabel("Seri Port:"))
        self.port_combo = QComboBox()
        control_layout.addWidget(self.port_combo)
        
        # Baud rate seçimi
        control_layout.addWidget(QLabel("Baud Rate:"))
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baudrate_combo.setCurrentText('9600')
        control_layout.addWidget(self.baudrate_combo)
        
        # Butonlar
        self.refresh_btn = QPushButton("Portları Yenile")
        self.refresh_btn.clicked.connect(self.update_port_list)
        control_layout.addWidget(self.refresh_btn)
        
        self.connect_btn = QPushButton("Bağlan")
        self.connect_btn.clicked.connect(self.toggle_connection)
        control_layout.addWidget(self.connect_btn)
        
        # Veri temizleme
        self.clear_btn = QPushButton("Grafikleri Temizle")
        self.clear_btn.clicked.connect(self.clear_data)
        control_layout.addWidget(self.clear_btn)
        
        # JSON yükleme butonu (kontrol panelinde de)
        self.load_json_control_btn = QPushButton("📂 JSON Yükle")
        self.load_json_control_btn.clicked.connect(self.load_data_json)
        control_layout.addWidget(self.load_json_control_btn)
        
        # Grafik kaydetme butonları
        self.save_graphs_btn = QPushButton("📸 Tüm Grafikleri Kaydet")
        self.save_graphs_btn.clicked.connect(self.save_all_graphs)
        control_layout.addWidget(self.save_graphs_btn)
        
        # Veri analizi butonu (kontrol panelinde de)
        self.analyze_control_btn = QPushButton("📊 Veri Analizi")
        self.analyze_control_btn.clicked.connect(self.show_analysis)
        control_layout.addWidget(self.analyze_control_btn)
        
        control_layout.addStretch()
        parent_layout.addWidget(control_group)
        
    def create_values_panel(self, parent_layout):
        """Anlık değerler panelini oluştur - tüm parametreler"""
        values_group = QGroupBox("Anlık Değerler")
        values_layout = QGridLayout(values_group)
        
        # Değer etiketleri - tüm parametreler
        self.value_labels = {}
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        
        labels = [
            ("Current", "Akım (A):", "0.00"),
            ("Voltage", "Gerilim (V):", "0.00"),
            ("Power", "Güç (W):", "0.00"),
            ("Distance", "Mesafe (km):", "0.000"),
            ("Hydrogen", "H₂ (L):", "0.000"),  # Yeni: Hidrojen tüketimi
            ("Efficiency", "1 m³ H₂ ile (km):", "0.00"),  # Değişti: 1 m³ ile gidilen yol
            ("RPM", "RPM:", "0"),
            ("ERPM", "ERPM:", "0"),
            ("Duty", "Duty (%):", "0.00")
        ]
        
        for i, (key, label_text, default_value) in enumerate(labels):
            label = QLabel(label_text)
            label.setFont(font)
            label.setStyleSheet("color: #ffffff; font-weight: bold;")
            
            value_label = QLabel(default_value)
            value_label.setFont(font)
            
            # Özel renkler
            if key == "Distance":
                value_label.setStyleSheet("QLabel { color: #FFD700; font-weight: bold; }")  # Altın sarısı
            elif key == "Hydrogen":
                value_label.setStyleSheet("QLabel { color: #00CED1; font-weight: bold; }")  # Turkuaz (H₂)
            elif key == "Efficiency":
                value_label.setStyleSheet("QLabel { color: #32CD32; font-weight: bold; }")  # Lime yeşili
            else:
                value_label.setStyleSheet("QLabel { color: #0066CC; font-weight: bold; }")
            
            value_label.setAlignment(Qt.AlignRight)
            
            values_layout.addWidget(label, i, 0)
            values_layout.addWidget(value_label, i, 1)
            
            self.value_labels[key] = value_label
        
        values_group.setMaximumWidth(300)
        values_group.setMaximumHeight(380)  # Yükseklik artırıldı
        parent_layout.addWidget(values_group)
        parent_layout.addStretch()
    
    def create_log_panel(self, parent_layout):
        """Log panelini ve kaydetme butonlarını oluştur"""
        log_group = QGroupBox("İşlem Geçmişi")
        log_layout = QVBoxLayout(log_group)
        
        # Log metin alanı
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Courier New';
                font-size: 10pt;
                border: 1px solid #555555;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Hidrojen girişi bölümü
        hydrogen_layout = QHBoxLayout()
        
        hydrogen_label = QLabel("Hidrojen Tüketimi (Litre):")
        hydrogen_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        hydrogen_layout.addWidget(hydrogen_label)
        
        self.hydrogen_input = QDoubleSpinBox()
        self.hydrogen_input.setRange(0.0, 100000.0)
        self.hydrogen_input.setDecimals(3)  # 3 ondalık basamak
        self.hydrogen_input.setSingleStep(0.1)  # 0.1 L adımlarla
        self.hydrogen_input.setValue(0.0)
        self.hydrogen_input.setSuffix(" L")
        self.hydrogen_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #00CED1;
                border: 2px solid #00CED1;
                padding: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
        """)
        self.hydrogen_input.valueChanged.connect(self.update_hydrogen_consumption)
        hydrogen_layout.addWidget(self.hydrogen_input)
        
        hydrogen_set_btn = QPushButton("🔄 Güncelle")
        hydrogen_set_btn.clicked.connect(self.update_hydrogen_consumption)
        hydrogen_set_btn.setStyleSheet("background-color: #00CED1; color: white; padding: 8px;")
        hydrogen_layout.addWidget(hydrogen_set_btn)
        
        hydrogen_reset_btn = QPushButton("🗑️ Sıfırla")
        hydrogen_reset_btn.clicked.connect(self.reset_hydrogen_consumption)
        hydrogen_reset_btn.setStyleSheet("background-color: #FF5722; color: white; padding: 8px;")
        hydrogen_layout.addWidget(hydrogen_reset_btn)
        
        hydrogen_layout.addStretch()
        log_layout.addLayout(hydrogen_layout)
        
        # Kaydetme butonları
        save_layout = QHBoxLayout()
        
        save_json_btn = QPushButton("📊 JSON Kaydet")
        save_json_btn.clicked.connect(self.save_data_json)
        save_json_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        save_layout.addWidget(save_json_btn)
        
        load_json_btn = QPushButton("📂 JSON Yükle")
        load_json_btn.clicked.connect(self.load_data_json)
        load_json_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px;")
        save_layout.addWidget(load_json_btn)
        
        analyze_btn = QPushButton("📈 Veri Analizi")
        analyze_btn.clicked.connect(self.show_analysis)
        analyze_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 8px;")
        save_layout.addWidget(analyze_btn)
        
        log_layout.addLayout(save_layout)
        parent_layout.addWidget(log_group)

    def create_graphs_panel(self, parent_layout):
        """Grafik panelini oluştur - 4 grafik"""
        graphs_group = QGroupBox("Grafikler")
        graphs_layout = QVBoxLayout(graphs_group)
        
        # Grafik widget'ı oluştur
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('#2b2b2b')
        graphs_layout.addWidget(self.graph_widget)
        
        # Alt grafikler oluştur - 4 tanesi
        self.plots = {}
        self.curves = {}
        
        plot_configs = [
            ('Speed', 'Hız (km/h)', '#FF6B35'),
            ('Current', 'Akım (A)', '#FF1744'),
            ('Voltage', 'Gerilim (V)', '#00C853'),
            ('Power', 'Güç (W)', '#FF9800')
        ]
        
        # 2 satır 2 sütun düzeni (2x2 grid)
        for i, (key, title, color) in enumerate(plot_configs):
            if i % 2 == 0 and i > 0:
                self.graph_widget.nextRow()
            
            plot = self.graph_widget.addPlot(title=title)
            plot.setLabel('bottom', 'Zaman (dakika)')
            plot.setLabel('left', title)
            plot.showGrid(x=True, y=True, alpha=0.3)
            
            # Plot stilini ayarla - koyu tema
            plot.getAxis('left').setPen('#cccccc')
            plot.getAxis('bottom').setPen('#cccccc')
            plot.setTitle(title, color='#ffffff', size='12pt')
            
            # Grid rengini ayarla
            plot.getAxis('left').setTextPen('#cccccc')
            plot.getAxis('bottom').setTextPen('#cccccc')
            
            # Sağ tık menüsü
            plot.setMenuEnabled(False)
            
            def make_context_menu_handler(graph_key, graph_title):
                def context_menu_handler(event):
                    if event.button() == Qt.RightButton:
                        global_pos = self.graph_widget.mapToGlobal(event.pos())
                        self.show_graph_context_menu(graph_key, graph_title, global_pos)
                return context_menu_handler
            
            plot.scene().sigMouseClicked.connect(make_context_menu_handler(key, title))
            
            # Veri eğrisi
            curve = plot.plot(pen=pg.mkPen(color, width=2), name=title, 
                            symbol='o', symbolSize=4, symbolBrush=color, symbolPen=color)
            
            # Crosshair
            vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FFFFFF', width=1, style=Qt.DashLine))
            hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#FFFFFF', width=1, style=Qt.DashLine))
            plot.addItem(vLine, ignoreBounds=True)
            plot.addItem(hLine, ignoreBounds=True)
            
            value_label = pg.TextItem(anchor=(0, 1), color='#FFFFFF', fill='#000000')
            plot.addItem(value_label, ignoreBounds=True)
            
            def make_mouse_moved_handler(plot_item, v_line, h_line, curve_item, value_label_item, data_key):
                def mouse_moved(evt):
                    try:
                        if isinstance(evt, tuple) and len(evt) > 0:
                            pos = evt[0]
                        else:
                            pos = evt
                        
                        if plot_item.sceneBoundingRect().contains(pos):
                            mousePoint = plot_item.vb.mapSceneToView(pos)
                            
                            v_line.setPos(mousePoint.x())
                            h_line.setPos(mousePoint.y())
                            
                            if data_key in self.telemetry_data and self.telemetry_data[data_key]['times']:
                                times = self.telemetry_data[data_key]['times']
                                values = self.telemetry_data[data_key]['values']
                                
                                if times and self.start_time:
                                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                                    
                                    target_time = mousePoint.x()
                                    if relative_times:
                                        closest_idx = min(range(len(relative_times)), 
                                                         key=lambda i: abs(relative_times[i] - target_time))
                                        
                                        if closest_idx < len(values):
                                            closest_value = values[closest_idx]
                                            closest_time = relative_times[closest_idx]
                                            
                                            value_label_item.setText(f'Zaman: {closest_time:.2f} dk\nDeğer: {closest_value:.2f}')
                                            value_label_item.setPos(mousePoint.x(), mousePoint.y())
                    except Exception as e:
                        pass
                
                return mouse_moved
            
            plot.scene().sigMouseMoved.connect(make_mouse_moved_handler(plot, vLine, hLine, curve, value_label, key))
            
            self.plots[key] = plot
            self.curves[key] = curve
        
        parent_layout.addWidget(graphs_group)

    def calculate_distance(self, current_speed, current_time):
        """Hız ve zaman farkından mesafe hesapla"""
        if self.last_speed_time is not None and current_speed > 0:
            # Zaman farkı (saniye cinsinden)
            time_diff = (current_time - self.last_speed_time)
            
            # Mesafe = Hız × Zaman
            # Hız km/h cinsinden, zaman saniye cinsinden
            # Sonuç km cinsinden
            distance_increment = (current_speed * time_diff) / 3600.0
            
            self.total_distance += distance_increment
        
        self.last_speed_time = current_time
    
    def update_hydrogen_consumption(self):
        """Hidrojen tüketimini güncelle ve verimlilik hesapla"""
        self.hydrogen_consumed_liters = self.hydrogen_input.value()
        
        # Verimlilik hesapla: km/m³
        if self.hydrogen_consumed_liters > 0:
            hydrogen_m3 = self.hydrogen_consumed_liters / 1000.0  # Litre → m³
            self.hydrogen_efficiency = self.total_distance / hydrogen_m3 if hydrogen_m3 > 0 else 0.0
        else:
            self.hydrogen_efficiency = 0.0
        
        # Göstergeleri güncelle
        if 'Hydrogen' in self.value_labels:
            self.value_labels['Hydrogen'].setText(f"{self.hydrogen_consumed_liters:.3f}")
        
        if 'Efficiency' in self.value_labels:
            self.value_labels['Efficiency'].setText(f"{self.hydrogen_efficiency:.2f}")
        
        # Log mesajı
        self.log_message(f"💧 Hidrojen: {self.hydrogen_consumed_liters:.3f} L | "
                        f"1 m³ ile: {self.hydrogen_efficiency:.2f} km")
        
        # Bilgi mesajı
        if self.hydrogen_efficiency > 0:
            QMessageBox.information(self, "Hidrojen Verimlilik Hesaplandı",
                                  f"📊 Hidrojen Verimlilik Raporu\n\n"
                                  f"🛣️ Toplam Mesafe: {self.total_distance:.3f} km\n"
                                  f"💧 Hidrojen Tüketimi: {self.hydrogen_consumed_liters:.3f} L\n"
                                  f"📦 Hidrojen Hacmi: {self.hydrogen_consumed_liters/1000:.3f} m³\n\n"
                                  f"✨ 1 m³ Hidrojen ile Gidilen Yol\n"
                                  f"   {self.hydrogen_efficiency:.2f} km\n\n"
                                  f"💡 Yani 1 metreküp (1000 L) hidrojen ile\n"
                                  f"   {self.hydrogen_efficiency:.2f} kilometre yol alınabilir.")
    
    def reset_hydrogen_consumption(self):
        """Hidrojen tüketimini sıfırla"""
        self.hydrogen_consumed_liters = 0.0
        self.hydrogen_efficiency = 0.0
        self.hydrogen_input.setValue(0.0)
        
        if 'Hydrogen' in self.value_labels:
            self.value_labels['Hydrogen'].setText("0.000")
        
        if 'Efficiency' in self.value_labels:
            self.value_labels['Efficiency'].setText("0.00")
        
        self.log_message("🗑️ Hidrojen tüketimi sıfırlandı")
    
    def calculate_efficiency_on_distance_change(self):
        """Mesafe değiştiğinde verimlilik otomatik hesapla"""
        if self.hydrogen_consumed_liters > 0:
            hydrogen_m3 = self.hydrogen_consumed_liters / 1000.0
            self.hydrogen_efficiency = self.total_distance / hydrogen_m3 if hydrogen_m3 > 0 else 0.0
            
            if 'Efficiency' in self.value_labels:
                self.value_labels['Efficiency'].setText(f"{self.hydrogen_efficiency:.2f}")

    def update_data(self, data):
        """Yeni veri geldiğinde güncelle"""
        data_type = data['type']
        value = data['value']
        timestamp = data['datetime']
        
        # İlk veri geldiğinde başlangıç zamanını ayarla
        if self.start_time is None:
            self.start_time = timestamp.timestamp()
        
        # Hız verisi geldiğinde mesafe hesapla
        if data_type == 'Speed':
            old_distance = self.total_distance
            self.calculate_distance(value, timestamp.timestamp())
            
            # Mesafe verisini de kaydet
            self.telemetry_data['Distance']['values'].append(self.total_distance)
            self.telemetry_data['Distance']['times'].append(timestamp.timestamp())
            
            # Maksimum veri noktası kontrolü
            if len(self.telemetry_data['Distance']['values']) > self.max_data_points:
                self.telemetry_data['Distance']['values'].pop(0)
                self.telemetry_data['Distance']['times'].pop(0)
            
            # Mesafe değerini güncelle
            if 'Distance' in self.value_labels:
                self.value_labels['Distance'].setText(f"{self.total_distance:.3f}")
            
            # Mesafe değiştiğinde verimlilik hesapla (otomatik)
            if old_distance != self.total_distance:
                self.calculate_efficiency_on_distance_change()
        
        # Diğer veri tipleri için güncelleme
        if data_type in self.telemetry_data:
            # Veriyi depola
            self.telemetry_data[data_type]['values'].append(value)
            self.telemetry_data[data_type]['times'].append(timestamp.timestamp())
            
            # Maksimum veri noktası sınırını kontrol et
            if len(self.telemetry_data[data_type]['values']) > self.max_data_points:
                self.telemetry_data[data_type]['values'].pop(0)
                self.telemetry_data[data_type]['times'].pop(0)
            
            # Anlık değeri güncelle - tüm değerler için
            if data_type in self.value_labels:
                if data_type in ['RPM', 'ERPM']:
                    self.value_labels[data_type].setText(f"{int(value)}")
                else:
                    self.value_labels[data_type].setText(f"{value:.2f}")
            
            # Hız gösterimini güncelle
            if data_type == 'Speed':
                self.speed_display.set_speed(value)
            
            # Grafiği güncelle - ana grafikler için
            if data_type in self.curves and data_type in ['Speed', 'Current', 'Voltage', 'Power']:
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times and self.start_time:
                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                    self.curves[data_type].setData(relative_times, values)
        
        # Log mesajı
        log_msg = f"{data['timestamp']} - {data_type}: {value}"
        if data_type == 'Speed':
            log_msg += f" | Mesafe: {self.total_distance:.3f} km"
            if self.hydrogen_efficiency > 0:
                log_msg += f" | 1m³ ile: {self.hydrogen_efficiency:.2f} km"
        self.log_message(log_msg)

    def clear_data(self):
        """Tüm veriyi ve grafikleri temizle"""
        # Başlangıç zamanını sıfırla
        self.start_time = None
        
        # Mesafe verilerini sıfırla
        self.total_distance = 0.0
        self.last_speed_time = None
        
        # Hidrojen verilerini KORUYALIM (kullanıcı manuel girdiği için)
        # self.hydrogen_consumed_liters = 0.0  # KALDIRILDI
        # self.hydrogen_efficiency = 0.0  # KALDIRILDI
        
        # Verimlilik yeniden hesapla (mesafe sıfırlandığında)
        self.calculate_efficiency_on_distance_change()
        
        for key in self.telemetry_data:
            self.telemetry_data[key]['values'].clear()
            self.telemetry_data[key]['times'].clear()
            
            if key in self.curves:
                self.curves[key].setData([], [])
                
            if key in self.value_labels:
                if key in ['RPM', 'ERPM']:
                    self.value_labels[key].setText("0")
                elif key == 'Distance':
                    self.value_labels[key].setText("0.000")
                elif key == 'Hydrogen':
                    self.value_labels[key].setText(f"{self.hydrogen_consumed_liters:.3f}")
                elif key == 'Efficiency':
                    self.value_labels[key].setText(f"{self.hydrogen_efficiency:.2f}")
                else:
                    self.value_labels[key].setText("0.00")
        
        # Hız gösterimini sıfırla
        self.speed_display.set_speed(0.0)
        
        self.log_message("🗑️ Telemetri verileri temizlendi (Hidrojen verileri korundu).")

    def save_data_json(self):
        """Veriyi JSON formatında kaydet - datetime anahtarlı yapı"""
        if not any(self.telemetry_data[key]['values'] for key in self.telemetry_data):
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek veri yok!")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "JSON Dosyası Kaydet", 
            f"telemetri_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json);;All files (*.*)"
        )
        
        if filename:
            try:
                # Tüm zaman damgalarını topla ve sırala
                all_timestamps = set()
                for key in self.telemetry_data:
                    all_timestamps.update(self.telemetry_data[key]['times'])
                
                all_timestamps = sorted(all_timestamps)
                
                # JSON için datetime anahtarlı veri yapısı oluştur
                json_data = {
                    'export_info': {
                        'export_time': datetime.now().isoformat(),
                        'total_records': len(all_timestamps),
                        'data_types': list(self.telemetry_data.keys()),
                        'format': 'datetime_keyed',
                        'total_distance_km': self.total_distance,
                        'hydrogen_consumed_liters': self.hydrogen_consumed_liters,  # Yeni
                        'hydrogen_efficiency_km_per_m3': self.hydrogen_efficiency  # Yeni
                    },
                    'data': {}
                }
                
                # Her zaman damgası için bir kayıt oluştur
                for timestamp in all_timestamps:
                    datetime_str = datetime.fromtimestamp(timestamp).isoformat()
                    record = {
                        'timestamp': timestamp,
                        'datetime': datetime_str
                    }
                    
                    # Bu zaman damgasında hangi veriler var?
                    for data_type in self.telemetry_data:
                        if timestamp in self.telemetry_data[data_type]['times']:
                            idx = self.telemetry_data[data_type]['times'].index(timestamp)
                            value = self.telemetry_data[data_type]['values'][idx]
                            record[data_type] = value
                        else:
                            record[data_type] = None
                    
                    json_data['data'][datetime_str] = record
                
                with open(filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
                
                self.log_message(f"💾 JSON kaydedildi: {len(all_timestamps)} kayıt, "
                               f"Mesafe: {self.total_distance:.3f} km, "
                               f"H₂: {self.hydrogen_consumed_liters:.3f} L, "
                               f"1m³ ile: {self.hydrogen_efficiency:.2f} km")
                
                QMessageBox.information(self, "Başarılı", 
                                      f"Veriler datetime anahtarlı JSON formatında kaydedildi!\n\n"
                                      f"📄 Dosya: {filename}\n"
                                      f"📊 Kayıt sayısı: {len(all_timestamps)}\n"
                                      f"📈 Veri tipleri: {len(self.telemetry_data)}\n"
                                      f"🛣️ Toplam Mesafe: {self.total_distance:.3f} km\n"
                                      f"💧 Hidrojen: {self.hydrogen_consumed_liters:.3f} L\n"
                                      f"✨ 1 m³ ile: {self.hydrogen_efficiency:.2f} km")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"JSON kaydetme hatası:\n{str(e)}")
    
    def load_data_json(self):
        """JSON dosyasından veri yükle"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "JSON Dosyası Aç", "",
            "JSON files (*.json);;All files (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as jsonfile:
                    json_data = json.load(jsonfile)
                
                # Format kontrolü
                if 'data' in json_data and isinstance(json_data['data'], dict):
                    # Datetime anahtarlı format
                    self.load_datetime_keyed_json(json_data, filename)
                else:
                    QMessageBox.warning(self, "Uyarı", "Desteklenmeyen JSON formatı!")
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"JSON yükleme hatası:\n{str(e)}")

    def load_datetime_keyed_json(self, json_data, filename):
        """Datetime anahtarlı JSON formatını yükle"""
        try:
            # Mevcut verileri temizle
            self.clear_data()
            
            # Export bilgilerini al
            export_info = json_data.get('export_info', {})
            total_records = export_info.get('total_records', 0)
            data_types = export_info.get('data_types', [])
            export_time = export_info.get('export_time', 'Bilinmiyor')
            saved_distance = export_info.get('total_distance_km', 0.0)
            saved_hydrogen = export_info.get('hydrogen_consumed_liters', 0.0)
            saved_efficiency = export_info.get('hydrogen_efficiency_km_per_m3', 0.0)
            
            # Veri kayıtlarını yükle
            data_records = json_data.get('data', {})
            loaded_count = 0
            
            # Her datetime anahtarı için veriyi işle
            for datetime_str, record in data_records.items():
                if isinstance(record, dict):
                    timestamp = record.get('timestamp')
                    if timestamp:
                        # Her veri tipi için değeri kontrol et
                        for data_type in self.telemetry_data.keys():
                            if data_type in record and record[data_type] is not None:
                                value = record[data_type]
                                
                                # Veriyi ekle
                                self.telemetry_data[data_type]['values'].append(float(value))
                                self.telemetry_data[data_type]['times'].append(float(timestamp))
                        
                        loaded_count += 1
            
            # Kaydedilmiş değerleri geri yükle
            if saved_distance > 0:
                self.total_distance = saved_distance
            
            if saved_hydrogen > 0:
                self.hydrogen_consumed_liters = saved_hydrogen
                self.hydrogen_input.setValue(saved_hydrogen)  # Float olarak ayarla
            
            if saved_efficiency > 0:
                self.hydrogen_efficiency = saved_efficiency
            
            # Veriyi zaman sırasına göre sırala
            for data_type in self.telemetry_data.keys():
                if self.telemetry_data[data_type]['times']:
                    paired_data = list(zip(
                        self.telemetry_data[data_type]['times'],
                        self.telemetry_data[data_type]['values']
                    ))
                    paired_data.sort(key=lambda x: x[0])
                    
                    times, values = zip(*paired_data) if paired_data else ([], [])
                    self.telemetry_data[data_type]['times'] = list(times)
                    self.telemetry_data[data_type]['values'] = list(values)
            
            # Grafikleri güncelle
            self.update_graphs_from_loaded_data()
            
            # Anlık değerleri son değerlerle güncelle
            self.update_current_values_from_loaded_data()
            
            # Hidrojen göstergelerini güncelle
            if 'Hydrogen' in self.value_labels:
                self.value_labels['Hydrogen'].setText(f"{self.hydrogen_consumed_liters:.3f}")
            
            if 'Efficiency' in self.value_labels:
                self.value_labels['Efficiency'].setText(f"{self.hydrogen_efficiency:.2f}")
            
            # Başarı mesajı
            self.log_message(f"📂 JSON yüklendi: {loaded_count} kayıt, "
                           f"Mesafe: {self.total_distance:.3f} km, "
                           f"H₂: {self.hydrogen_consumed_liters:.3f} L, "
                           f"1m³ ile: {self.hydrogen_efficiency:.2f} km")
            
            QMessageBox.information(self, "Başarılı", 
                                  f"JSON dosyası başarıyla yüklendi!\n\n"
                                  f"📄 Dosya: {filename.split('/')[-1]}\n"
                                  f"📊 Yüklenen kayıt: {loaded_count}\n"
                                  f"📈 Veri tipleri: {len([dt for dt in data_types if dt in self.telemetry_data])}\n"
                                  f"🛣️ Toplam Mesafe: {self.total_distance:.3f} km\n"
                                  f"💧 Hidrojen: {self.hydrogen_consumed_liters:.3f} L\n"
                                  f"✨ 1 m³ ile: {self.hydrogen_efficiency:.2f} km\n"
                                  f"📅 Export zamanı: {export_time}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"JSON veri işleme hatası:\n{str(e)}")
    
    def show_analysis(self):
        """Veri analizi penceresini göster"""
        if not any(self.telemetry_data[key]['values'] for key in self.telemetry_data):
            QMessageBox.warning(self, "Uyarı", "Analiz edilecek veri yok!")
            return
        
        analysis_dialog = DataAnalysisDialog(self.telemetry_data, self)
        analysis_dialog.exec_()

    def show_graph_context_menu(self, graph_key, graph_title, pos):
        """Grafik için sağ tık menüsü göster"""
        menu = QMenu(self)
        
        save_png_action = QAction(f"📷 {graph_title} PNG olarak kaydet", self)
        save_png_action.triggered.connect(lambda: self.save_graph_as_image(graph_key, graph_title, 'png'))
        menu.addAction(save_png_action)
        
        save_svg_action = QAction(f"📊 {graph_title} SVG olarak kaydet", self)
        save_svg_action.triggered.connect(lambda: self.save_graph_as_image(graph_key, graph_title, 'svg'))
        menu.addAction(save_svg_action)
        
        menu.addSeparator()
        
        save_all_png_action = QAction("📷 Tüm Grafikleri PNG olarak kaydet", self)
        save_all_png_action.triggered.connect(lambda: self.save_all_graphs('png'))
        menu.addAction(save_all_png_action)
        
        save_all_svg_action = QAction("📊 Tüm Grafikleri SVG olarak kaydet", self)
        save_all_svg_action.triggered.connect(lambda: self.save_all_graphs('svg'))
        menu.addAction(save_all_svg_action)
        
        menu.exec_(pos)
    
    def save_graph_as_image(self, graph_key, graph_title, format_type='png'):
        """Tek bir grafiği resim olarak kaydet"""
        if graph_key not in self.plots:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"{graph_title} Kaydet",
            f"{graph_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}",
            f"{format_type.upper()} files (*.{format_type});;All files (*.*)"
        )
        
        if filename:
            try:
                exporter = pg.exporters.ImageExporter(self.plots[graph_key].plotItem)
                exporter.export(filename)
                self.log_message(f"💾 Grafik kaydedildi: {filename}")
                QMessageBox.information(self, "Başarılı", f"{graph_title} grafiği kaydedildi!")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Grafik kaydetme hatası:\n{str(e)}")
    
    def save_all_graphs(self, format_type='png'):
        """Tüm grafikleri resim olarak kaydet"""
        folder = QFileDialog.getExistingDirectory(self, "Grafiklerin Kaydedileceği Klasörü Seç")
        
        if folder:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                saved_count = 0
                
                for graph_key, plot in self.plots.items():
                    filename = os.path.join(folder, f"{graph_key}_{timestamp}.{format_type}")
                    exporter = pg.exporters.ImageExporter(plot.plotItem)
                    exporter.export(filename)
                    saved_count += 1
                
                self.log_message(f"💾 {saved_count} grafik kaydedildi: {folder}")
                QMessageBox.information(self, "Başarılı", 
                                      f"{saved_count} grafik başarıyla kaydedildi!\n\n"
                                      f"📁 Konum: {folder}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Grafik kaydetme hatası:\n{str(e)}")
    
    def update_port_list(self):
        """Mevcut seri portları ve TCP simulatörünü listele"""
        self.port_combo.clear()
        
        # Sanal Arduino simulatörünü ekle
        self.port_combo.addItem("🖥️ Virtual Arduino Simulator (TCP)")
        
        # Gerçek seri portları tara
        ports = serial.tools.list_ports.comports()
        
        if ports:
            for port in ports:
                self.port_combo.addItem(f"{port.device} - {port.description}")
            self.log_message(f"✓ Virtual Arduino + {len(ports)} seri port bulundu")
        else:
            self.log_message("✓ Virtual Arduino hazır (seri port yok)")
    
    def toggle_connection(self):
        """Seri port veya TCP bağlantısını aç/kapat"""
        if self.serial_thread and self.serial_thread.is_running:
            # Bağlantıyı kes
            self.serial_thread.stop()
            self.serial_thread.wait()
            self.serial_thread = None
            
            self.connect_btn.setText("Bağlan")
            self.connect_btn.setStyleSheet("")
            self.refresh_btn.setEnabled(True)
            self.port_combo.setEnabled(True)
            self.baudrate_combo.setEnabled(True)
            
            self.log_message("❌ Bağlantı kesildi")
        else:
            # Bağlan
            port_text = self.port_combo.currentText()
            if not port_text or port_text == "Port bulunamadı":
                QMessageBox.warning(self, "Uyarı", "Geçerli bir port seçin!")
                return
            
            try:
                # Virtual Arduino kontrolü
                if "Virtual Arduino" in port_text:
                    # TCP bağlantısı
                    self.serial_thread = TCPThread('localhost', 9999)
                    self.log_message("🖥️ Virtual Arduino'ya bağlanılıyor (TCP)...")
                else:
                    # Gerçek seri port bağlantısı
                    port = port_text.split(' - ')[0]
                    baudrate = int(self.baudrate_combo.currentText())
                    self.serial_thread = SerialThread(port, baudrate)
                    self.log_message(f"📡 {port} portuna bağlanılıyor...")
                
                # Sinyalleri bağla
                self.serial_thread.data_received.connect(self.update_data)
                self.serial_thread.error_occurred.connect(self.handle_error)
                self.serial_thread.start()
                
                # UI güncellemeleri
                self.connect_btn.setText("Bağlantıyı Kes")
                self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white;")
                self.refresh_btn.setEnabled(False)
                self.port_combo.setEnabled(False)
                self.baudrate_combo.setEnabled(False)
                
                if "Virtual Arduino" in port_text:
                    self.log_message("✓ Virtual Arduino bağlantısı kuruldu (localhost:9999)")
                else:
                    self.log_message(f"✓ Seri port bağlantısı kuruldu")
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Bağlantı hatası:\n{str(e)}")
                self.log_message(f"❌ Bağlantı hatası: {str(e)}")
    
    def update_graphs_from_loaded_data(self):
        """Yüklenen verilerden grafikleri güncelle"""
        all_times = []
        for data_type in self.telemetry_data:
            if self.telemetry_data[data_type]['times']:
                all_times.extend(self.telemetry_data[data_type]['times'])
        
        if all_times:
            self.start_time = min(all_times)
        
        # Sadece 4 grafik için güncelleme
        for data_type in ['Speed', 'Current', 'Voltage', 'Power']:
            if data_type in self.curves and data_type in self.telemetry_data:
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times and values and self.start_time:
                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                    self.curves[data_type].setData(relative_times, values)
    
    def update_current_values_from_loaded_data(self):
        """Yüklenen verilerden anlık değerleri güncelle"""
        for data_type in self.value_labels.keys():
            if (data_type in self.telemetry_data and 
                self.telemetry_data[data_type]['values']):
                
                last_value = self.telemetry_data[data_type]['values'][-1]
                
                if data_type in ['RPM', 'ERPM']:
                    self.value_labels[data_type].setText(f"{int(last_value)}")
                elif data_type == 'Distance':
                    self.value_labels[data_type].setText(f"{last_value:.3f}")
                else:
                    self.value_labels[data_type].setText(f"{last_value:.2f}")
                
                if data_type == 'Speed':
                    self.speed_display.set_speed(last_value)

    def handle_error(self, error_message):
        """Hata mesajlarını işle"""
        self.log_message(f"HATA: {error_message}")
        QMessageBox.critical(self, "Bağlantı Hatası", error_message)
        
        # Bağlantıyı sıfırla
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_btn.setText("Bağlan")
            self.connect_btn.setStyleSheet("")
    
    def log_message(self, message):
        """Log mesajı ekle"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def closeEvent(self, event):
        """Uygulama kapatılırken temizlik yap"""
        if self.serial_thread and self.serial_thread.is_running:
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = TelemetryApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()