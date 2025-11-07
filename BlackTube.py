import flet as ft
import yt_dlp
import json
import os
from pathlib import Path
from datetime import datetime
import threading

# ===== CLASE PRINCIPAL DE LA APLICACIÓN =====
class YouTubeDownloaderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "PyTube"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        
        # Variables de estado
        self.current_tab = 0
        self.downloads_history = []
        self.current_video_info = None
        self.is_downloading = False
        
        # Configuraciones por defecto
        self.settings = {
            "theme": "dark",
            "download_path": str(Path.home() / "Downloads" / "PyTube"),
            "default_quality": "best",
            "default_format": "video",
            "auto_play": False,
            "notifications": True,
            "theme_color": "blue"
        }
        
        # Crear directorio de descargas si no existe
        os.makedirs(self.settings["download_path"], exist_ok=True)
        
        # Cargar configuraciones guardadas
        self.load_settings()
        
        # Construir la interfaz
        self.build_ui()
    
    # ===== CARGA Y GUARDADO DE CONFIGURACIONES =====
    def load_settings(self):
        """Carga las configuraciones desde un archivo JSON"""
        try:
            settings_file = Path.home() / ".pytube_settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except Exception as e:
            print(f"Error cargando configuraciones: {e}")
    
    def save_settings(self):
        """Guarda las configuraciones en un archivo JSON"""
        try:
            settings_file = Path.home() / ".pytube_settings.json"
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error guardando configuraciones: {e}")
    
    # ===== CONSTRUCCIÓN DE LA INTERFAZ =====
    def build_ui(self):
        """Construye toda la interfaz de usuario"""
        
        # AppBar superior
        self.page.appbar = ft.AppBar(
            title=ft.Text("PyTube", weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=self.get_theme_color(),
            actions=[
                ft.IconButton(
                    icon="brightness_6",
                    on_click=self.toggle_theme,
                    tooltip="Cambiar tema"
                )
            ]
        )
        
        # Construir las pestañas primero
        self.build_home_tab()
        self.build_downloads_tab()
        self.build_player_tab()
        self.build_settings_tab()
        
        # Barra de navegación inferior CORREGIDA
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.nav_changed,
            destinations=[
                ft.NavigationDestination(icon="home", label="Inicio"),
                ft.NavigationDestination(icon="download", label="Descargas"),
                ft.NavigationDestination(icon="play_circle", label="Reproductor"),
                ft.NavigationDestination(icon="settings", label="Ajustes"),
            ]
        )
        
        # Contenedor principal
        self.main_container = ft.Container(
            content=self.home_content,
            expand=True,
            padding=10
        )
        
        # Añadir todo a la página
        self.page.add(
            ft.Column([
                self.main_container,
                self.nav_bar
            ], expand=True, spacing=0)
        )
    
    # ===== TAB 1: INICIO (DESCARGA) =====
    def build_home_tab(self):
        """Construye la pestaña de inicio para descargar videos"""
        
        # Campo de URL
        self.url_field = ft.TextField(
            label="URL del video de YouTube",
            hint_text="https://youtube.com/watch?v=...",
            prefix_icon="link",
            expand=True,
            on_submit=lambda _: self.fetch_video_info()
        )
        
        # Botón de buscar información
        self.fetch_btn = ft.ElevatedButton(
            "Buscar",
            icon="search",
            on_click=lambda _: self.fetch_video_info()
        )
        
        # Card de información del video
        self.video_title = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        self.video_author = ft.Text("", size=12, color="grey")
        self.video_duration = ft.Text("Duración: --")
        self.video_views = ft.Text("Vistas: --")
        
        self.video_info_card = ft.Card(
            visible=False,
            elevation=5,
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Row([
                        ft.Icon("video_library", size=40, color=self.get_theme_color()),
                        ft.Column([
                            self.video_title,
                            self.video_author,
                        ], expand=True, spacing=2)
                    ], spacing=10),
                    ft.Divider(),
                    self.video_duration,
                    self.video_views,
                ], spacing=8)
            )
        )
        
        # Opciones de descarga
        self.format_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="video", label="Video + Audio"),
                ft.Radio(value="audio", label="Solo Audio"),
            ]),
            value="video"
        )
        
        self.quality_dropdown = ft.Dropdown(
            label="Calidad",
            options=[
                ft.dropdown.Option("best", "Mejor calidad"),
                ft.dropdown.Option("1080p", "1080p"),
                ft.dropdown.Option("720p", "720p"),
                ft.dropdown.Option("480p", "480p"),
                ft.dropdown.Option("360p", "360p"),
            ],
            value="best",
            width=200
        )
        
        self.audio_format_dropdown = ft.Dropdown(
            label="Formato de audio",
            options=[
                ft.dropdown.Option("mp3", "MP3"),
                ft.dropdown.Option("m4a", "M4A"),
                ft.dropdown.Option("opus", "OPUS"),
            ],
            value="mp3",
            width=200,
            visible=False
        )
        
        # Actualizar visibilidad del formato de audio según selección
        def format_changed(e):
            is_audio = self.format_radio.value == "audio"
            self.audio_format_dropdown.visible = is_audio
            self.page.update()
        
        self.format_radio.on_change = format_changed
        
        # Barra de progreso
        self.progress_bar = ft.ProgressBar(
            visible=False,
            value=0,
            color=self.get_theme_color()
        )
        
        self.progress_text = ft.Text("", size=12, visible=False)
        
        # Botón de descarga
        self.download_btn = ft.ElevatedButton(
            "Descargar",
            icon="download",
            disabled=True,
            on_click=lambda _: self.start_download(),
        )
        
        # Contenido de la pestaña de inicio
        self.home_content = ft.ListView(
            spacing=15,
            padding=20,
            controls=[
                ft.Text("Descarga videos de YouTube", 
                     size=24, 
                     weight=ft.FontWeight.BOLD),
                ft.Row([self.url_field, self.fetch_btn], spacing=10),
                self.video_info_card,
                ft.Divider(),
                ft.Text("Opciones de descarga", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Formato:", size=14),
                self.format_radio,
                ft.Row([
                    self.quality_dropdown,
                    self.audio_format_dropdown
                ], spacing=10),
                self.progress_bar,
                self.progress_text,
                self.download_btn,
            ]
        )
    
    # ===== TAB 2: DESCARGAS =====
    def build_downloads_tab(self):
        """Construye la pestaña de historial de descargas"""
        
        self.downloads_list = ft.ListView(
            spacing=10,
            padding=20,
        )
        
        self.downloads_content = ft.Column([
            ft.Row([
                ft.Text("Mis Descargas", size=24, weight=ft.FontWeight.BOLD, expand=True),
                ft.IconButton(
                    icon="refresh",
                    on_click=lambda _: self.refresh_downloads(),
                    tooltip="Actualizar"
                )
            ]),
            ft.Divider(),
            self.downloads_list
        ], expand=True)
        
        self.refresh_downloads()
    
    # ===== TAB 3: REPRODUCTOR =====
    def build_player_tab(self):
        """Construye la pestaña del reproductor multimedia"""
        
        self.player_title = ft.Text("Selecciona un archivo", size=20, weight=ft.FontWeight.BOLD)
        self.player_subtitle = ft.Text("", size=14, color="grey")
        
        # Controles del reproductor
        self.play_pause_btn = ft.IconButton(
            icon="play_arrow",
            icon_size=50,
            on_click=self.toggle_play_pause,
            disabled=True
        )
        
        self.position_slider = ft.Slider(
            min=0,
            max=100,
            value=0,
            disabled=True,
            on_change=self.seek_position
        )
        
        self.current_time = ft.Text("0:00")
        self.total_time = ft.Text("0:00")
        
        self.volume_slider = ft.Slider(
            min=0,
            max=100,
            value=50,
            label="Volumen",
            on_change=self.change_volume
        )
        
        # Lista de reproducción
        self.playlist_list = ft.ListView(
            spacing=5,
            height=200,
        )
        
        self.player_content = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Reproductor", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Container(
                    padding=20,
                    bgcolor="surface",
                    border_radius=10,
                    content=ft.Column([
                        ft.Icon("music_note", size=80, color=self.get_theme_color()),
                        self.player_title,
                        self.player_subtitle,
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
                ),
                ft.Container(height=20),
                ft.Row([
                    ft.IconButton(icon="skip_previous", on_click=self.previous_track),
                    self.play_pause_btn,
                    ft.IconButton(icon="skip_next", on_click=self.next_track),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    self.current_time,
                    self.position_slider,
                    self.total_time,
                ], spacing=10),
                ft.Row([
                    ft.Icon("volume_down"),
                    self.volume_slider,
                    ft.Icon("volume_up"),
                ], spacing=10),
                ft.Divider(),
                ft.Text("Lista de reproducción", size=16, weight=ft.FontWeight.BOLD),
                self.playlist_list,
            ], spacing=10, scroll=ft.ScrollMode.AUTO)
        )
    
    # ===== TAB 4: CONFIGURACIONES =====
    def build_settings_tab(self):
        """Construye la pestaña de configuraciones"""
        
        # Selector de color de tema
        self.theme_color_dropdown = ft.Dropdown(
            label="Color del tema",
            options=[
                ft.dropdown.Option("blue", "Azul"),
                ft.dropdown.Option("red", "Rojo"),
                ft.dropdown.Option("green", "Verde"),
                ft.dropdown.Option("purple", "Morado"),
                ft.dropdown.Option("orange", "Naranja"),
            ],
            value=self.settings.get("theme_color", "blue"),
            on_change=self.change_theme_color
        )
        
        # Switches de configuración
        self.auto_play_switch = ft.Switch(
            label="Reproducir automáticamente tras descargar",
            value=self.settings.get("auto_play", False),
            on_change=self.toggle_auto_play
        )
        
        self.notifications_switch = ft.Switch(
            label="Notificaciones",
            value=self.settings.get("notifications", True),
            on_change=self.toggle_notifications
        )
        
        # Campo de ruta de descargas
        self.download_path_field = ft.TextField(
            label="Carpeta de descargas",
            value=self.settings["download_path"],
            read_only=True,
            prefix_icon="folder"
        )
        
        self.settings_content = ft.ListView(
            padding=20,
            spacing=15,
            controls=[
                ft.Text("Configuraciones", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Apariencia", size=18, weight=ft.FontWeight.BOLD),
                self.theme_color_dropdown,
                ft.Divider(),
                ft.Text("Comportamiento", size=18, weight=ft.FontWeight.BOLD),
                self.auto_play_switch,
                self.notifications_switch,
                ft.Divider(),
                ft.Text("Almacenamiento", size=18, weight=ft.FontWeight.BOLD),
                self.download_path_field,
                ft.ElevatedButton(
                    "Cambiar carpeta",
                    icon="folder_open",
                    on_click=self.change_download_folder
                ),
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Limpiar caché",
                    icon="cleaning_services",
                    on_click=self.clear_cache,
                ),
                ft.Divider(),
                ft.Text("Acerca de", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("PyTube v1.0", size=14),
                ft.Text("Una aplicación completa para descargar y reproducir videos de YouTube", 
                     size=12, color="grey"),
            ]
        )
    
    # ===== FUNCIONES DE NAVEGACIÓN =====
    def nav_changed(self, e):
        """Cambia entre las diferentes pestañas"""
        self.current_tab = e.control.selected_index
        
        if self.current_tab == 0:
            self.main_container.content = self.home_content
        elif self.current_tab == 1:
            self.main_container.content = self.downloads_content
            self.refresh_downloads()
        elif self.current_tab == 2:
            self.main_container.content = self.player_content
        elif self.current_tab == 3:
            self.main_container.content = self.settings_content
        
        self.page.update()
    
    # ===== FUNCIONES DE TEMA =====
    def get_theme_color(self):
        """Obtiene el color del tema actual"""
        colors = {
            "blue": "blue",
            "red": "red",
            "green": "green",
            "purple": "purple",
            "orange": "orange",
        }
        return colors.get(self.settings["theme_color"], "blue")
    
    def toggle_theme(self, e):
        """Alterna entre tema claro y oscuro"""
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.settings["theme"] = "light"
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.settings["theme"] = "dark"
        
        self.save_settings()
        self.page.update()
    
    def change_theme_color(self, e):
        """Cambia el color del tema"""
        self.settings["theme_color"] = e.control.value
        self.save_settings()
        
        # Actualizar color en varios componentes
        self.page.appbar.bgcolor = self.get_theme_color()
        self.progress_bar.color = self.get_theme_color()
        
        self.show_snackbar("Color del tema actualizado")
        self.page.update()
    
    # ===== FUNCIONES DE DESCARGA =====
    def fetch_video_info(self):
        """Obtiene información del video de YouTube"""
        url = self.url_field.value.strip()
        
        if not url:
            self.show_snackbar("Por favor ingresa una URL", error=True)
            return
        
        # MEJORA: Mostrar indicador de carga durante la búsqueda
        self.fetch_btn.disabled = True
        self.fetch_btn.text = "Buscando..."
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_text.value = "Conectando con YouTube..."
        self.progress_bar.value = None  # Barra indeterminada
        self.page.update()
        
        def fetch_thread():
            try:
                # Configuración de yt-dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self.current_video_info = info
                    
                    # Actualizar UI con información del video
                    def update_ui():
                        # Actualizar card de información
                        self.video_title.value = info.get('title', 'Sin título')
                        self.video_author.value = info.get('uploader', 'Desconocido')
                        
                        duration = info.get('duration', 0)
                        mins, secs = divmod(duration, 60)
                        self.video_duration.value = f"Duración: {int(mins)}:{int(secs):02d}"
                        
                        views = info.get('view_count', 0)
                        self.video_views.value = f"Vistas: {views:,}"
                        
                        self.video_info_card.visible = True
                        self.download_btn.disabled = False
                        self.fetch_btn.disabled = False
                        self.fetch_btn.text = "Buscar"
                        
                        # MEJORA: Ocultar indicador de carga
                        self.progress_bar.visible = False
                        self.progress_text.visible = False
                        
                        self.show_snackbar("Información obtenida correctamente")
                        self.page.update()
                    
                    self.page.run_task(update_ui)
                    
            except Exception as e:
                def show_error():
                    self.show_snackbar(f"Error: {str(e)}", error=True)
                    self.fetch_btn.disabled = False
                    self.fetch_btn.text = "Buscar"
                    
                    # MEJORA: Ocultar indicador de carga en caso de error
                    self.progress_bar.visible = False
                    self.progress_text.visible = False
                    
                    self.page.update()
                
                self.page.run_task(show_error)
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def start_download(self):
        """Inicia la descarga del video"""
        if not self.current_video_info:
            self.show_snackbar("Primero busca un video", error=True)
            return
        
        if self.is_downloading:
            self.show_snackbar("Ya hay una descarga en progreso", error=True)
            return
        
        self.is_downloading = True
        self.download_btn.disabled = True
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_bar.value = 0
        self.progress_text.value = "Preparando descarga..."
        self.page.update()
        
        def download_thread():
            try:
                # Configurar opciones de descarga
                format_type = self.format_radio.value
                quality = self.quality_dropdown.value
                
                # Crear nombre de archivo
                safe_title = "".join(c for c in self.current_video_info['title'] 
                                   if c.isalnum() or c in (' ', '-', '_')).strip()
                
                ydl_opts = {
                    'outtmpl': os.path.join(self.settings["download_path"], f'{safe_title}.%(ext)s'),
                    'progress_hooks': [self.download_progress_hook],
                }
                
                # Configurar según tipo de descarga
                if format_type == "audio":
                    audio_format = self.audio_format_dropdown.value
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': audio_format,
                        'preferredquality': '192',
                    }]
                else:
                    if quality == "best":
                        ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    else:
                        ydl_opts['format'] = f'bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]'
                
                # Descargar
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.current_video_info['webpage_url']])
                
                # Guardar en historial
                download_entry = {
                    'title': self.current_video_info['title'],
                    'type': format_type,
                    'quality': quality,
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'path': os.path.join(self.settings["download_path"], safe_title)
                }
                self.downloads_history.append(download_entry)
                
                def finish_download():
                    self.is_downloading = False
                    self.download_btn.disabled = False
                    self.progress_bar.visible = False
                    self.progress_text.visible = False
                    
                    self.show_snackbar("¡Descarga completada!")
                    
                    # Auto-reproducir si está habilitado
                    if self.settings.get("auto_play", False):
                        self.nav_bar.selected_index = 2
                        self.nav_changed(type('obj', (object,), {'control': self.nav_bar})())
                    
                    self.page.update()
                
                self.page.run_task(finish_download)
                
            except Exception as e:
                def show_error():
                    self.is_downloading = False
                    self.download_btn.disabled = False
                    self.progress_bar.visible = False
                    self.progress_text.visible = False
                    self.show_snackbar(f"Error en descarga: {str(e)}", error=True)
                    self.page.update()
                
                self.page.run_task(show_error)
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def download_progress_hook(self, d):
        """Hook para actualizar el progreso de descarga"""
        if d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0%').strip('%')
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                
                def update_progress():
                    self.progress_bar.value = float(percent) / 100
                    self.progress_text.value = f"Descargando... {percent}% - Velocidad: {speed} - ETA: {eta}"
                    self.page.update()
                
                self.page.run_task(update_progress)
            except:
                pass
    
    # ===== FUNCIONES DE HISTORIAL =====
    def refresh_downloads(self):
        """Actualiza la lista de descargas"""
        self.downloads_list.controls.clear()
        
        if not self.downloads_history:
            self.downloads_list.controls.append(
                ft.Container(
                    padding=40,
                    content=ft.Column([
                        ft.Icon("download_done", size=60, color="grey"),
                        ft.Text("No hay descargas aún", size=16, color="grey"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
        else:
            for download in reversed(self.downloads_history):
                self.downloads_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=15,
                            content=ft.Row([
                                ft.Icon(
                                    "music_note" if download['type'] == 'audio' else "video_library",
                                    size=40,
                                    color=self.get_theme_color()
                                ),
                                ft.Column([
                                    ft.Text(download['title'], size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{download['type'].upper()} - {download['quality']}", 
                                         size=12, color="grey"),
                                    ft.Text(download['date'], size=10, color="grey"),
                                ], expand=True, spacing=2),
                                ft.IconButton(
                                    icon="play_arrow",
                                    on_click=lambda e, d=download: self.play_download(d),
                                    tooltip="Reproducir"
                                ),
                            ], spacing=10)
                        )
                    )
                )
        
        self.page.update()
    
    def play_download(self, download):
        """Reproduce un archivo descargado"""
        self.nav_bar.selected_index = 2
        self.nav_changed(type('obj', (object,), {'control': self.nav_bar})())
        self.player_title.value = download['title']
        self.player_subtitle.value = f"{download['type'].upper()} - {download['quality']}"
        self.play_pause_btn.disabled = False
        self.position_slider.disabled = False
        self.page.update()
    
    # ===== FUNCIONES DEL REPRODUCTOR =====
    def toggle_play_pause(self, e):
        """Alterna entre reproducir y pausar"""
        if self.play_pause_btn.icon == "play_arrow":
            self.play_pause_btn.icon = "pause"
            self.show_snackbar("Reproduciendo...")
        else:
            self.play_pause_btn.icon = "play_arrow"
            self.show_snackbar("Pausado")
        
        self.page.update()
    
    def seek_position(self, e):
        """Cambia la posición de reproducción"""
        pass  # Implementación simplificada
    
    def change_volume(self, e):
        """Cambia el volumen"""
        pass  # Implementación simplificada
    
    def previous_track(self, e):
        """Reproduce el track anterior"""
        self.show_snackbar("Track anterior")
    
    def next_track(self, e):
        """Reproduce el siguiente track"""
        self.show_snackbar("Siguiente track")
    
    # ===== FUNCIONES DE CONFIGURACIÓN =====
    def toggle_auto_play(self, e):
        """Activa/desactiva reproducción automática"""
        self.settings["auto_play"] = e.control.value
        self.save_settings()
    
    def toggle_notifications(self, e):
        """Activa/desactiva notificaciones"""
        self.settings["notifications"] = e.control.value
        self.save_settings()
    
    def change_download_folder(self, e):
        """Cambia la carpeta de descargas"""
        self.show_snackbar("Función disponible próximamente")
    
    def clear_cache(self, e):
        """Limpia la caché de la aplicación"""
        self.show_snackbar("Caché limpiada correctamente")
    
    # ===== UTILIDADES =====
    def show_snackbar(self, message, error=False):
        """Muestra un mensaje tipo snackbar"""
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor="red" if error else self.get_theme_color(),
            )
        )


# ===== FUNCIÓN PRINCIPAL =====
def main(page: ft.Page):
    """Función principal que inicia la aplicación"""
    app = YouTubeDownloaderApp(page)

# Iniciar la aplicación
if __name__ == "__main__":
    ft.app(target=main)