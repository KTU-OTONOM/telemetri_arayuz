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
                             QFileDialog, QSpinBox, QMenu, QAction, QDialog,
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
        self.max_data_points = 1000  # Maksimum veri noktası sayısı
        self.serial_thread = None
        self.start_time = None  # Başlangıç zamanını takip etmek için
        
        # Veri depolama - sadece ihtiyaç duyulan veriler
        self.telemetry_data = {
            'Speed': {'values': [], 'times': []},
            'Current': {'values': [], 'times': []},
            'Voltage': {'values': [], 'times': []},
            'Power': {'values': [], 'times': []},
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
        self.analyze_control_btn.clicked.connect(self.show_data_analysis)
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
            ("RPM", "RPM:", "0"),
            ("ERPM", "ERPM:", "0"),
            ("Duty", "Duty (%):", "0.00")
        ]
        
        for i, (key, label_text, default_value) in enumerate(labels):
            label = QLabel(label_text)
            label.setFont(font)
            label.setStyleSheet("color: #ffffff; font-weight: bold;")  # Beyaz renk
            
            value_label = QLabel(default_value)
            value_label.setFont(font)
            value_label.setStyleSheet("QLabel { color: #0066CC; font-weight: bold; }")
            value_label.setAlignment(Qt.AlignRight)
            
            values_layout.addWidget(label, i, 0)
            values_layout.addWidget(value_label, i, 1)
            
            self.value_labels[key] = value_label
        
        values_group.setMaximumWidth(300)
        values_group.setMaximumHeight(280)
        parent_layout.addWidget(values_group)
        parent_layout.addStretch()
        
    def create_graphs_panel(self, parent_layout):
        """Grafik panelini oluştur - 4 grafik (duty olmadan)"""
        graphs_group = QGroupBox("Grafikler")
        graphs_layout = QVBoxLayout(graphs_group)
        
        # Grafik widget'ı oluştur
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.graph_widget.setBackground('#2b2b2b')  # Koyu arkaplan
        graphs_layout.addWidget(self.graph_widget)
        
        # Alt grafikler oluştur - 4 tanesi (duty olmadan)
        self.plots = {}
        self.curves = {}
        
        plot_configs = [
            ('Speed', 'Hız (km/h)', '#FF6B35'),
            ('Current', 'Akım (A)', '#FF1744'),
            ('Voltage', 'Gerilim (V)', '#00C853'),
            ('Power', 'Güç (W)', '#FF9800')
        ]
        
        for i, (key, title, color) in enumerate(plot_configs):
            if i % 2 == 0 and i > 0:
                self.graph_widget.nextRow()
            
            plot = self.graph_widget.addPlot(title=title)
            plot.setLabel('bottom', 'Zaman (dakika)')  # Zaman ekseni dakika olarak değiştirildi
            plot.setLabel('left', title)
            plot.showGrid(x=True, y=True, alpha=0.3)
            
            # Plot stilini ayarla - koyu tema
            plot.getAxis('left').setPen('#cccccc')
            plot.getAxis('bottom').setPen('#cccccc')
            plot.setTitle(title, color='#ffffff', size='12pt')
            
            # Grid rengini ayarla
            plot.getAxis('left').setTextPen('#cccccc')
            plot.getAxis('bottom').setTextPen('#cccccc')
            
            # Sağ tık menüsü için plot widget'ına özel özellik ekle
            plot.setMenuEnabled(False)  # Varsayılan menüyü devre dışı bırak
            
            # Custom context menu için mouse event'i ekle
            def make_context_menu_handler(graph_key, graph_title):
                def context_menu_handler(event):
                    if event.button() == Qt.RightButton:
                        # Global koordinatları al
                        global_pos = self.graph_widget.mapToGlobal(event.pos())
                        self.show_graph_context_menu(graph_key, graph_title, global_pos)
                return context_menu_handler
            
            # Mouse press event'ini bağla
            plot.scene().sigMouseClicked.connect(make_context_menu_handler(key, title))
            
            # Veri noktası değerlerini göstermek için crosshair ekleme
            curve = plot.plot(pen=pg.mkPen(color, width=2), name=title, 
                            symbol='o', symbolSize=4, symbolBrush=color, symbolPen=color)
            
            # Crosshair (fare imleciyle veri değeri gösterme)
            vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FFFFFF', width=1, style=Qt.DashLine))
            hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#FFFFFF', width=1, style=Qt.DashLine))
            plot.addItem(vLine, ignoreBounds=True)
            plot.addItem(hLine, ignoreBounds=True)
            
            # Değer gösterme label'ı
            value_label = pg.TextItem(anchor=(0, 1), color='#FFFFFF', fill='#000000')
            plot.addItem(value_label, ignoreBounds=True)
            
            # Mouse move event'ini bağla
            def make_mouse_moved_handler(plot_item, v_line, h_line, curve_item, value_label_item, data_key):
                def mouse_moved(evt):
                    try:
                        # PyQtGraph sürümüne göre evt parametresini kontrol et
                        if isinstance(evt, tuple) and len(evt) > 0:
                            # Eski PyQtGraph sürümü (tuple olarak gelir)
                            pos = evt[0]
                        else:
                            # Yeni PyQtGraph sürümü (doğrudan QPointF olarak gelir)
                            pos = evt
                        
                        if plot_item.sceneBoundingRect().contains(pos):
                            mousePoint = plot_item.vb.mapSceneToView(pos)
                            
                            # Crosshair'ı güncelle
                            v_line.setPos(mousePoint.x())
                            h_line.setPos(mousePoint.y())
                            
                            # En yakın veri noktasını bul ve değeri göster
                            if data_key in self.telemetry_data and self.telemetry_data[data_key]['times']:
                                times = self.telemetry_data[data_key]['times']
                                values = self.telemetry_data[data_key]['values']
                                
                                if times and self.start_time:
                                    # Dakika cinsinden relative times
                                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                                    
                                    # En yakın noktayı bul
                                    target_time = mousePoint.x()
                                    if relative_times:
                                        closest_idx = min(range(len(relative_times)), 
                                                         key=lambda i: abs(relative_times[i] - target_time))
                                        
                                        if closest_idx < len(values):
                                            closest_value = values[closest_idx]
                                            closest_time = relative_times[closest_idx]
                                            
                                            # Değeri göster
                                            value_label_item.setText(f'Zaman: {closest_time:.2f} dk\nDeğer: {closest_value:.2f}')
                                            value_label_item.setPos(mousePoint.x(), mousePoint.y())
                    except Exception as e:
                        # Hataları sessizce yakala ve devam et
                        pass
                
                return mouse_moved
            
            plot.scene().sigMouseMoved.connect(make_mouse_moved_handler(plot, vLine, hLine, curve, value_label, key))
            
            self.plots[key] = plot
            self.curves[key] = curve
        
        parent_layout.addWidget(graphs_group)
    
    def save_single_graph(self, graph_key, graph_title):
        """Tek bir grafiği kaydet"""
        if graph_key not in self.plots:
            QMessageBox.warning(self, "Hata", f"Grafik bulunamadı: {graph_title}")
            return
        
        # Dosya adını oluştur
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"{graph_title.replace(' ', '_').replace('(', '').replace(')', '')}_{timestamp}.png"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"{graph_title} Grafiği Kaydet", 
            default_filename,
            "PNG files (*.png);;JPG files (*.jpg)"
        )
        
        if filename:
            try:
                # Yöntem 1: PyQtGraph exporters ile dene
                try:
                    plot_widget = self.plots[graph_key]
                    
                    # Farklı exporter import yöntemlerini dene
                    try:
                        from pyqtgraph.exporters import ImageExporter
                        exporter = ImageExporter(plot_widget)
                    except ImportError:
                        import pyqtgraph.exporters
                        exporter = pyqtgraph.exporters.ImageExporter(plot_widget)
                    
                    exporter.parameters()['width'] = 1200
                    exporter.parameters()['height'] = 800
                    exporter.export(filename)
                    
                    self.log_message(f"📸 Grafik kaydedildi (PyQtGraph): {graph_title} -> {filename}")
                    QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi:\n{filename}")
                    return
                    
                except Exception as e:
                    self.log_message(f"⚠️ PyQtGraph exporters hatası: {e}")
                
                # Yöntem 2: QPixmap ile screenshot
                try:
                    plot_widget = self.plots[graph_key]
                    pixmap = plot_widget.grab()
                    pixmap.save(filename)
                    
                    self.log_message(f"📸 Grafik kaydedildi (QPixmap): {graph_title} -> {filename}")
                    QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi (screenshot):\n{filename}")
                    return
                    
                except Exception as e:
                    self.log_message(f"⚠️ QPixmap hatası: {e}")
                
                # Yöntem 3: Matplotlib alternatifi
                self.log_message(f"🔄 Matplotlib alternatifi kullanılıyor...")
                self.save_graph_with_matplotlib(graph_key, graph_title, filename)
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Grafik kaydetme hatası:\n{str(e)}")
    
    def save_graph_with_matplotlib(self, graph_key, graph_title, filename):
        """Matplotlib ile grafik kaydet (alternatif yöntem)"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.dates import DateFormatter
            import matplotlib.dates as mdates
            
            # Veriyi al
            if graph_key not in self.telemetry_data:
                raise Exception(f"Veri bulunamadı: {graph_key}")
            
            times = self.telemetry_data[graph_key]['times']
            values = self.telemetry_data[graph_key]['values']
            
            if not times or not values:
                raise Exception("Grafik verisi boş!")
            
            # Zaman verilerini datetime'a çevir
            datetime_times = [datetime.fromtimestamp(t) for t in times]
            
            # Matplotlib grafiği oluştur
            plt.figure(figsize=(12, 8))
            plt.plot(datetime_times, values, marker='o', markersize=2, linewidth=1.5)
            plt.title(graph_title, fontsize=16, fontweight='bold')
            plt.xlabel('Zaman', fontsize=12)
            plt.ylabel(graph_title, fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Zaman ekseni formatla
            plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self.log_message(f"📸 Matplotlib ile grafik kaydedildi: {graph_title} -> {filename}")
            QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi (matplotlib):\n{filename}")
            
        except ImportError:
            QMessageBox.critical(self, "Hata", "Matplotlib kurulu değil!\npip install matplotlib")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Matplotlib grafik kaydetme hatası:\n{str(e)}")
    
    def save_all_graphs(self):
        """Tüm grafikleri tek dosyada kaydet"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"telemetri_grafikleri_{timestamp}.png"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Tüm Grafikler Kaydet", 
            default_filename,
            "PNG files (*.png);;JPG files (*.jpg)"
        )
        
        if filename:
            try:
                # Yöntem 1: PyQtGraph exporters ile dene
                try:
                    try:
                        from pyqtgraph.exporters import ImageExporter
                        exporter = ImageExporter(self.graph_widget)
                    except ImportError:
                        import pyqtgraph.exporters
                        exporter = pyqtgraph.exporters.ImageExporter(self.graph_widget)
                    
                    exporter.parameters()['width'] = 1600
                    exporter.parameters()['height'] = 1200
                    exporter.export(filename)
                    
                    self.log_message(f"📸 Tüm grafikler kaydedildi (PyQtGraph): {filename}")
                    QMessageBox.information(self, "Başarılı", f"Tüm grafikler kaydedildi:\n{filename}")
                    return
                    
                except Exception as e:
                    self.log_message(f"⚠️ PyQtGraph exporters hatası: {e}")
                
                # Yöntem 2: QPixmap ile screenshot
                try:
                    pixmap = self.graph_widget.grab()
                    pixmap.save(filename)
                    
                    self.log_message(f"📸 Tüm grafikler kaydedildi (QPixmap): {filename}")
                    QMessageBox.information(self, "Başarılı", f"Tüm grafikler kaydedildi (screenshot):\n{filename}")
                    return
                    
                except Exception as e:
                    self.log_message(f"⚠️ QPixmap hatası: {e}")
                
                # Yöntem 3: Matplotlib alternatifi
                self.log_message(f"🔄 Matplotlib alternatifi kullanılıyor...")
                self.save_all_graphs_with_matplotlib(filename)
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Grafik kaydetme hatası:\n{str(e)}")
    
    def save_all_graphs_with_matplotlib(self, filename):
        """Matplotlib ile tüm grafikleri kaydet"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.dates import DateFormatter
            import matplotlib.dates as mdates
            
            # 2x2 subplot düzeni
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Arduino Telemetri Grafikleri', fontsize=16, fontweight='bold')
            
            plot_configs = [
                ('Speed', 'Hız (km/h)', '#FF6B35'),
                ('Current', 'Akım (A)', '#FF1744'),
                ('Voltage', 'Gerilim (V)', '#00C853'),
                ('Power', 'Güç (W)', '#FF9800')
            ]
            
            for i, (key, title, color) in enumerate(plot_configs):
                row = i // 2
                col = i % 2
                ax = axes[row, col]
                
                if key in self.telemetry_data:
                    times = self.telemetry_data[key]['times']
                    values = self.telemetry_data[key]['values']
                    
                    if times and values:
                        datetime_times = [datetime.fromtimestamp(t) for t in times]
                        ax.plot(datetime_times, values, color=color, marker='o', markersize=1, linewidth=1)
                        ax.set_title(title, fontweight='bold')
                        ax.set_xlabel('Zaman')
                        ax.set_ylabel(title)
                        ax.grid(True, alpha=0.3)
                        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
                        
                        # X ekseni etiketlerini döndür
                        for label in ax.get_xticklabels():
                            label.set_rotation(45)
                    else:
                        ax.text(0.5, 0.5, 'Veri Yok', ha='center', va='center', transform=ax.transAxes)
                        ax.set_title(title, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            self.log_message(f"📸 Matplotlib ile tüm grafikler kaydedildi: {filename}")
            QMessageBox.information(self, "Başarılı", f"Tüm grafikler kaydedildi (matplotlib):\n{filename}")
            
        except ImportError:
            QMessageBox.critical(self, "Hata", "Matplotlib kurulu değil!\npip install matplotlib")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Matplotlib grafik kaydetme hatası:\n{str(e)}")
    
    def show_graph_context_menu(self, graph_key, graph_title, position):
        """Grafik için sağ tık menüsü göster"""
        context_menu = QMenu(self)
        
        # Tek grafik kaydetme
        save_action = QAction(f"📸 {graph_title} Grafiğini Kaydet", self)
        save_action.triggered.connect(lambda: self.save_single_graph(graph_key, graph_title))
        context_menu.addAction(save_action)
        
        # Ayırıcı
        context_menu.addSeparator()
        
        # Tüm grafikler kaydetme
        save_all_action = QAction("📸 Tüm Grafikleri Kaydet", self)
        save_all_action.triggered.connect(self.save_all_graphs)
        context_menu.addAction(save_all_action)
        
        # Grafik temizleme
        clear_action = QAction(f"🗑️ {graph_title} Grafiğini Temizle", self)
        clear_action.triggered.connect(lambda: self.clear_single_graph(graph_key, graph_title))
        context_menu.addAction(clear_action)
        
        # Menüyü göster
        context_menu.exec_(position)
    
    def clear_single_graph(self, graph_key, graph_title):
        """Tek bir grafiği temizle"""
        if graph_key in self.telemetry_data:
            self.telemetry_data[graph_key]['values'].clear()
            self.telemetry_data[graph_key]['times'].clear()
            
            if graph_key in self.curves:
                self.curves[graph_key].setData([], [])
            
            if graph_key in self.value_labels:
                self.value_labels[graph_key].setText("0.00")
            
            # Hız gösterimini de güncelle
            if graph_key == 'Speed':
                self.speed_display.set_speed(0.0)
        
        self.log_message(f"🗑️ {graph_title} grafiği temizlendi.")
        
    def create_log_panel(self, parent_layout):
        """Log ve kaydetme panelini oluştur"""
        log_group = QGroupBox("Log ve Kaydetme")
        log_layout = QVBoxLayout(log_group)
        
        # Üst kısım - kontroller
        top_layout = QHBoxLayout()
        
        # Maksimum veri noktası ayarı
        top_layout.addWidget(QLabel("Maks. Veri Noktası:"))
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 10000)
        self.max_points_spin.setValue(self.max_data_points)
        self.max_points_spin.valueChanged.connect(self.update_max_points)
        top_layout.addWidget(self.max_points_spin)
        
        top_layout.addStretch()
        
        # Kaydetme butonları
        self.save_csv_btn = QPushButton("CSV Olarak Kaydet")
        self.save_csv_btn.clicked.connect(self.save_data_csv)
        top_layout.addWidget(self.save_csv_btn)
        
        self.save_json_btn = QPushButton("JSON Olarak Kaydet")
        self.save_json_btn.clicked.connect(self.save_data_json)
        top_layout.addWidget(self.save_json_btn)
        
        # JSON dosyası yükleme butonu
        self.load_json_btn = QPushButton("📂 JSON Dosyası Yükle")
        self.load_json_btn.clicked.connect(self.load_data_json)
        top_layout.addWidget(self.load_json_btn)
        
        # JSON analiz butonu
        self.analyze_json_btn = QPushButton("📊 Veri Analizi")
        self.analyze_json_btn.clicked.connect(self.show_data_analysis)
        top_layout.addWidget(self.analyze_json_btn)
        
        # Tekil grafik kaydetme - güncellenen seçenekler
        top_layout.addWidget(QLabel("Grafik Kaydet:"))
        self.graph_combo = QComboBox()
        self.graph_combo.addItem("Tüm Grafikler")
        self.graph_combo.addItem("Hız Grafiği")
        self.graph_combo.addItem("Akım Grafiği")
        self.graph_combo.addItem("Gerilim Grafiği")
        self.graph_combo.addItem("Güç Grafiği")
        top_layout.addWidget(self.graph_combo)
        
        self.save_graph_btn = QPushButton("📸 Grafik Kaydet")
        self.save_graph_btn.clicked.connect(self.save_selected_graph)
        top_layout.addWidget(self.save_graph_btn)
        
        log_layout.addLayout(top_layout)
        
        # Ortada - Log text alanı ve logolar
        middle_layout = QHBoxLayout()
        
        # Sol taraf - Log text alanı
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        middle_layout.addWidget(self.log_text, 3)  # 3/4 genişlik
        
        # Sağ taraf - Takım logoları
        logos_layout = QVBoxLayout()
        
        # KATOT logosu
        katot_logo_path = os.path.join('images', 'katot.png')
        if os.path.exists(katot_logo_path):
            katot_label = QLabel()
            katot_pixmap = QPixmap(katot_logo_path)
            if not katot_pixmap.isNull():
                # Logoyu eski boyutlandır
                scaled_katot = katot_pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                katot_label.setPixmap(scaled_katot)
                katot_label.setAlignment(Qt.AlignCenter)
                katot_label.setStyleSheet("border: 1px solid #555555; border-radius: 4px; padding: 5px; background-color: rgba(255, 255, 255, 20);")
                logos_layout.addWidget(katot_label)
        
        # Boşluk
        logos_layout.addSpacing(10)
        
        # KTECH logosu
        ktech_logo_path = os.path.join('images', 'ktech.png')
        if os.path.exists(ktech_logo_path):
            ktech_label = QLabel()
            ktech_pixmap = QPixmap(ktech_logo_path)
            if not ktech_pixmap.isNull():
                # Logoyu eski boyutlandır
                scaled_ktech = ktech_pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ktech_label.setPixmap(scaled_ktech)
                ktech_label.setAlignment(Qt.AlignCenter)
                ktech_label.setStyleSheet("border: 1px solid #555555; border-radius: 4px; padding: 5px; background-color: rgba(255, 255, 255, 20);")
                logos_layout.addWidget(ktech_label)
        
        logos_layout.addStretch()
        middle_layout.addLayout(logos_layout, 1)  # 1/4 genişlik
        
        log_layout.addLayout(middle_layout)
        
        log_group.setMaximumHeight(250)
        parent_layout.addWidget(log_group)
    
    def save_selected_graph(self):
        """Seçilen grafiği kaydet"""
        selected_text = self.graph_combo.currentText()
        
        # Grafik mapping - güncellendi
        graph_mapping = {
            "Tüm Grafikler": None,
            "Hız Grafiği": ("Speed", "Hız (km/h)"),
            "Akım Grafiği": ("Current", "Akım (A)"),
            "Gerilim Grafiği": ("Voltage", "Gerilim (V)"),
            "Güç Grafiği": ("Power", "Güç (W)")
        }
        
        if selected_text == "Tüm Grafikler":
            self.save_all_graphs()
        elif selected_text in graph_mapping:
            graph_key, graph_title = graph_mapping[selected_text]
            self.save_single_graph(graph_key, graph_title)
        else:
            QMessageBox.warning(self, "Hata", "Geçersiz grafik seçimi!")
        
    def update_port_list(self):
        """Mevcut seri portları listele"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        arduino_ports = []
        esp_ports = []
        other_ports = []
        
        for port in ports:
            # Port tipini sınıflandır
            port_icon, port_category = classify_port(port)
            
            # VID/PID bilgisi varsa ekle
            vid_pid_info = ""
            if hasattr(port, 'vid') and hasattr(port, 'pid') and port.vid and port.pid:
                vid_pid_info = f" [VID:PID={port.vid:04X}:{port.pid:04X}]"
            
            # Detaylı port bilgisi oluştur
            port_info = f"{port.device} - {port_icon} - {port.description}{vid_pid_info}"
            
            # Port kategorisine göre grupla
            if port_category in ["Arduino", "ESP"]:
                if port_category == "Arduino":
                    arduino_ports.append(port_info)
                else:
                    esp_ports.append(port_info)
            else:
                other_ports.append(port_info)
        
        # Virtual port seçeneği ekle
        self.port_combo.addItem("🖥️ Virtual Arduino Simulator - TCP localhost:9999")
        
        # Öncelik sırası: Virtual -> Arduino -> ESP -> Diğerleri
        all_ports = arduino_ports + esp_ports + other_ports
        for port_info in all_ports:
            self.port_combo.addItem(port_info)
        
        if not ports:
            self.port_combo.addItem("❌ Port bulunamadı")
        
        # Log mesajı
        total_ports = len(ports)
        arduino_count = len(arduino_ports)
        esp_count = len(esp_ports)
        self.log_message(f"📡 Port taraması: {total_ports} port bulundu (Arduino: {arduino_count}, ESP: {esp_count}, Diğer: {len(other_ports)})")
            
    def toggle_connection(self):
        """Seri port/TCP bağlantısını aç/kapat"""
        if self.serial_thread and self.serial_thread.is_running:
            # Bağlantıyı kes
            self.serial_thread.stop()
            self.serial_thread.wait()
            self.serial_thread = None
            
            self.connect_btn.setText("Bağlan")
            self.connect_btn.setStyleSheet("")
            self.log_message("🔌 Bağlantı kesildi.")
            
        else:
            # Bağlantı kur
            current_port_text = self.port_combo.currentText()
            if "❌ Port bulunamadı" in current_port_text:
                QMessageBox.warning(self, "Hata", "Geçerli bir port seçin!")
                return
            
            # Virtual port kontrolü
            if "🖥️ Virtual Arduino Simulator" in current_port_text:
                # TCP bağlantısı
                host = "localhost"
                tcp_port = 9999
                port_type = "Virtual Arduino (TCP)"
                
                self.serial_thread = TCPThread(host, tcp_port)
                self.serial_thread.data_received.connect(self.update_data)
                self.serial_thread.error_occurred.connect(self.handle_error)
                self.serial_thread.start()
                
                self.connect_btn.setText("Bağlantıyı Kes")
                self.connect_btn.setStyleSheet("background-color: red; color: white;")
                self.log_message(f"🖥️ Virtual Arduino bağlantısı kuruldu: {host}:{tcp_port}")
                return
                
            # Port adını ayıkla (emoji ve açıklamadan temizle)
            port = current_port_text.split(" - ")[0]
            baudrate = int(self.baudrate_combo.currentText())
            
            # Port tipini belirle
            if "🔧 Arduino" in current_port_text:
                port_type = "Arduino"
            elif "🌐 ESP Board" in current_port_text:
                port_type = "ESP Board"
            elif "📶 Bluetooth" in current_port_text:
                port_type = "Bluetooth"
                # Bluetooth bağlantısı için uyarı ver
                reply = QMessageBox.question(self, "Bluetooth Bağlantısı", 
                                           f"Bluetooth port ({port}) seçtiniz.\n"
                                           "Bu port genelde Arduino bağlantısı için uygun değildir.\n"
                                           "Arduino'nuz Bluetooth modülü ile mi bağlı?\n\n"
                                           "Devam etmek istiyor musunuz?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            elif "🔌 USB Serial" in current_port_text:
                port_type = "USB Serial"
            elif "📟 Serial" in current_port_text:
                port_type = "Serial"
            else:
                port_type = "Bilinmeyen"
            
            self.serial_thread = SerialThread(port, baudrate)
            self.serial_thread.data_received.connect(self.update_data)
            self.serial_thread.error_occurred.connect(self.handle_error)
            self.serial_thread.start()
            
            self.connect_btn.setText("Bağlantıyı Kes")
            self.connect_btn.setStyleSheet("background-color: red; color: white;")
            self.log_message(f"📡 Bağlantı kuruldu: {port} ({port_type}) @ {baudrate} baud")
            
    def update_data(self, data):
        """Yeni veri geldiğinde güncelle"""
        data_type = data['type']
        value = data['value']
        timestamp = data['datetime']
        
        # İlk veri geldiğinde başlangıç zamanını ayarla
        if self.start_time is None:
            self.start_time = timestamp.timestamp()
        
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
                    # RPM ve ERPM için tam sayı göster
                    self.value_labels[data_type].setText(f"{int(value)}")
                else:
                    # Diğerleri için ondalıklı göster
                    self.value_labels[data_type].setText(f"{value:.2f}")
            
            # Hız gösterimini güncelle
            if data_type == 'Speed':
                self.speed_display.set_speed(value)
            
            # Grafiği güncelle - sadece ana 4 grafik için
            if data_type in self.curves and data_type in ['Speed', 'Current', 'Voltage', 'Power']:
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times and self.start_time:
                    # Zaman eksenini dakika cinsinden relative yapmak için ilk zamanı çıkar ve 60'a böl
                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                    self.curves[data_type].setData(relative_times, values)
        
        # Log mesajı
        log_msg = f"{data['timestamp']} - {data_type}: {value}"
        self.log_message(log_msg)
    
    def clear_data(self):
        """Tüm veriyi ve grafikleri temizle"""
        # Başlangıç zamanını sıfırla
        self.start_time = None
        
        for key in self.telemetry_data:
            self.telemetry_data[key]['values'].clear()
            self.telemetry_data[key]['times'].clear()
            
            if key in self.curves:
                self.curves[key].setData([], [])
                
            if key in self.value_labels:
                if key in ['RPM', 'ERPM']:
                    self.value_labels[key].setText("0")
                else:
                    self.value_labels[key].setText("0.00")
        
        # Hız gösterimini sıfırla
        self.speed_display.set_speed(0.0)
        
        self.log_message("Tüm veriler temizlendi.")
    
    def update_max_points(self):
        """Maksimum veri noktası sayısını güncelle"""
        self.max_data_points = self.max_points_spin.value()
        self.log_message(f"Maksimum veri noktası sayısı: {self.max_data_points} olarak güncellendi.")
        
        # Mevcut verileri sınırla
        for data_type in self.telemetry_data:
            if len(self.telemetry_data[data_type]['values']) > self.max_data_points:
                # Son N veriyi al
                self.telemetry_data[data_type]['values'] = self.telemetry_data[data_type]['values'][-self.max_data_points:]
                self.telemetry_data[data_type]['times'] = self.telemetry_data[data_type]['times'][-self.max_data_points:]
                
                # Grafikleri güncelle
                if data_type in self.curves and data_type in ['Speed', 'Current', 'Voltage', 'Power']:
                    times = self.telemetry_data[data_type]['times']
                    values = self.telemetry_data[data_type]['values']
                    
                    if times and self.start_time:
                        relative_times = [(t - self.start_time) / 60.0 for t in times]
                        self.curves[data_type].setData(relative_times, values)
    
    def update_graphs_from_loaded_data(self):
        """Yüklenen verilerden grafikleri güncelle"""
        # JSON yüklendiğinde başlangıç zamanını ayarla
        all_times = []
        for data_type in self.telemetry_data:
            if self.telemetry_data[data_type]['times']:
                all_times.extend(self.telemetry_data[data_type]['times'])
        
        if all_times:
            self.start_time = min(all_times)
        
        for data_type in ['Speed', 'Current', 'Voltage', 'Power']:
            if data_type in self.curves and data_type in self.telemetry_data:
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times and values and self.start_time:
                    # Zaman eksenini dakika cinsinden relative yapmak için ilk zamanı çıkar ve 60'a böl
                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                    self.curves[data_type].setData(relative_times, values)

    def save_data_csv(self):
        """Veriyi CSV formatında kaydet"""
        if not any(self.telemetry_data[key]['values'] for key in self.telemetry_data):
            QMessageBox.warning(self, "Uyarı", "Kaydedilecek veri yok!")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV Dosyası Kaydet", 
            f"telemetri_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Header
                    headers = ['Timestamp', 'DateTime'] + list(self.telemetry_data.keys())
                    writer.writerow(headers)
                    
                    # Tüm zaman damgalarını topla
                    all_times = set()
                    for key in self.telemetry_data:
                        all_times.update(self.telemetry_data[key]['times'])
                    
                    all_times = sorted(all_times)
                    
                    # Her zaman damgası için satır yaz
                    for timestamp in all_times:
                        row = [timestamp, datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')]
                        
                        for key in self.telemetry_data:
                            # Bu zaman damgasında bu veri var mı?
                            if timestamp in self.telemetry_data[key]['times']:
                                idx = self.telemetry_data[key]['times'].index(timestamp)
                                value = self.telemetry_data[key]['values'][idx]
                                row.append(value)
                            else:
                                row.append('')  # Boş değer
                        
                        writer.writerow(row)
                
                self.log_message(f"Veriler CSV olarak kaydedildi: {filename}")
                QMessageBox.information(self, "Başarılı", f"Veriler kaydedildi:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"CSV kaydetme hatası:\n{str(e)}")
                
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
                        'format': 'datetime_keyed'
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
                            record[data_type] = None  # Bu zaman damgasında bu veri yok
                    
                    json_data['data'][datetime_str] = record
                
                with open(filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump(json_data, jsonfile, indent=2, ensure_ascii=False)
                
                self.log_message(f"💾 JSON kaydedildi: {len(all_timestamps)} kayıt, {filename}")
                QMessageBox.information(self, "Başarılı", 
                                      f"Veriler datetime anahtarlı JSON formatında kaydedildi!\n\n"
                                      f"📄 Dosya: {filename}\n"
                                      f"📊 Kayıt sayısı: {len(all_timestamps)}\n"
                                      f"📈 Veri tipleri: {len(self.telemetry_data)}\n\n"
                                      f"Analiz için: python analyze_telemetry.py \"{''.join(filename.split('/')[-1])}\"")
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"JSON kaydetme hatası:\n{str(e)}")
    
    def load_data_json(self):
        """JSON dosyasından veri yükle"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "JSON Dosyası Yükle", 
            "",
            "JSON files (*.json);;All files (*.*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as jsonfile:
                    json_data = json.load(jsonfile)
                
                # Dosya formatını kontrol et
                if 'export_info' in json_data and 'data' in json_data:
                    # Yeni format - datetime anahtarlı
                    self.load_datetime_keyed_json(json_data, filename)
                else:
                    # Eski format veya farklı format
                    QMessageBox.warning(self, "Uyarı", 
                                      "Bu JSON dosyası desteklenen formatta değil!\n"
                                      "Sadece bu uygulamayla kaydedilmiş JSON dosyaları yüklenebilir.")
                    return
                
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Hata", "Geçersiz JSON dosyası!")
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
            
            # Veriyi zaman sırasına göre sırala
            for data_type in self.telemetry_data.keys():
                if self.telemetry_data[data_type]['times']:
                    # Zip ile eşleştir, sırala, sonra ayır
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
            
            # Başarı mesajı
            self.log_message(f"📂 JSON dosyası yüklendi: {loaded_count} kayıt, {filename}")
            QMessageBox.information(self, "Başarılı", 
                                  f"JSON dosyası başarıyla yüklendi!\n\n"
                                  f"📄 Dosya: {filename.split('/')[-1]}\n"
                                  f"📊 Yüklenen kayıt: {loaded_count}\n"
                                  f"📈 Veri tipleri: {len([dt for dt in data_types if dt in self.telemetry_data])}\n"
                                  f"📅 Export zamanı: {export_time}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"JSON veri işleme hatası:\n{str(e)}")
    
    def show_data_analysis(self):
        """Veri analizi penceresini göster"""
        # Veri var mı kontrol et
        has_data = any(self.telemetry_data[key]['values'] for key in self.telemetry_data)
        
        if not has_data:
            QMessageBox.warning(self, "Uyarı", 
                              "Analiz edilecek veri bulunamadı!\n\n"
                              "Veri toplamak için:\n"
                              "1. Arduino'yu bağlayın ve veri toplayın\n"
                              "   VEYA\n"
                              "2. JSON dosyası yükleyin")
            return
        
        try:
            # Analiz penceresini aç
            dialog = DataAnalysisDialog(self.telemetry_data, self)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Analiz penceresi açılırken hata:\n{str(e)}")
    
    def update_graphs_from_loaded_data(self):
        """Yüklenen verilerden grafikleri güncelle"""
        # JSON yüklendiğinde başlangıç zamanını ayarla
        all_times = []
        for data_type in self.telemetry_data:
            if self.telemetry_data[data_type]['times']:
                all_times.extend(self.telemetry_data[data_type]['times'])
        
        if all_times:
            self.start_time = min(all_times)
        
        for data_type in ['Speed', 'Current', 'Voltage', 'Power']:
            if data_type in self.curves and data_type in self.telemetry_data:
                times = self.telemetry_data[data_type]['times']
                values = self.telemetry_data[data_type]['values']
                
                if times and values and self.start_time:
                    # Zaman eksenini dakika cinsinden relative yapmak için ilk zamanı çıkar ve 60'a böl
                    relative_times = [(t - self.start_time) / 60.0 for t in times]
                    self.curves[data_type].setData(relative_times, values)

    def update_current_values_from_loaded_data(self):
        """Yüklenen verilerden anlık değerleri güncelle"""
        for data_type in self.value_labels.keys():
            if (data_type in self.telemetry_data and 
                self.telemetry_data[data_type]['values']):
                
                # Son değeri al
                last_value = self.telemetry_data[data_type]['values'][-1]
                
                if data_type in ['RPM', 'ERPM']:
                    self.value_labels[data_type].setText(f"{int(last_value)}")
                else:
                    self.value_labels[data_type].setText(f"{last_value:.2f}")
                
                # Hız gösterimini de güncelle
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